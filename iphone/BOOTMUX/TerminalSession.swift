import Foundation
import SwiftUI

enum TerminalTransportMessage {
    case string(String)
    case data(Data)
}

protocol TerminalTransport: AnyObject {
    func resume()
    func receive() async throws -> TerminalTransportMessage
    func send(_ text: String) async throws
    func close()
}

final class URLSessionTerminalTransport: TerminalTransport {
    private let socket: URLSessionWebSocketTask

    init(url: URL) {
        socket = URLSession.shared.webSocketTask(with: url)
    }

    func resume() { socket.resume() }

    func receive() async throws -> TerminalTransportMessage {
        switch try await socket.receive() {
        case .string(let value): return .string(value)
        case .data(let value): return .data(value)
        @unknown default: throw ProtocolError.malformed
        }
    }

    func send(_ text: String) async throws { try await socket.send(.string(text)) }
    func close() { socket.cancel(with: .goingAway, reason: nil) }
}

@MainActor
final class TerminalSession: ObservableObject {
    enum HandleResult { case continueReceiving, terminal }

    enum State: Equatable {
        case disconnected
        case connecting
        case connected(String)
        case closing
        case failed(String)

        var label: String {
            switch self {
            case .disconnected: return "OFF"
            case .connecting: return "CONNECTING"
            case .connected: return "ON"
            case .closing: return "CLOSING"
            case .failed: return "ERROR"
            }
        }
    }

    @Published private(set) var state: State = .disconnected
    @Published private(set) var terminalText = ""
    @Published private(set) var statusMessage = "Disconnected."

    private let transportFactory: (URL) -> any TerminalTransport
    private let maxFrameBytes = 131_072
    private var transport: (any TerminalTransport)?
    private var generation = 0
    private var publishToken = 0
    private var buffer = TerminalBuffer()
    private var sanitizer = ANSISanitizer()
    private var publishTask: Task<Void, Never>?

    init(transportFactory: @escaping (URL) -> any TerminalTransport = { URLSessionTerminalTransport(url: $0) }) {
        self.transportFactory = transportFactory
    }

    func connect(endpoint: String) {
        guard case .disconnected = state else {
            statusMessage = "Already connected or connecting."
            return
        }
        guard let url = URL(string: endpoint), ["ws", "wss"].contains(url.scheme?.lowercased() ?? ""), url.user == nil, url.password == nil else {
            state = .failed("Enter a ws:// or wss:// endpoint without credentials.")
            return
        }
        generation += 1
        let currentGeneration = generation
        publishToken += 1
        publishTask?.cancel()
        publishTask = nil
        buffer.clear()
        terminalText = ""
        sanitizer = ANSISanitizer()
        state = .connecting
        statusMessage = "Connecting."
        let socket = transportFactory(url)
        transport = socket
        socket.resume()
        Task { [weak self, weak socket] in
            guard let self, let socket else { return }
            await self.receiveLoop(socket: socket, generation: currentGeneration)
        }
    }

    func disconnect() {
        let oldTransport = transport
        let sessionID = currentSessionID
        generation += 1
        publishToken += 1
        publishTask?.cancel()
        publishTask = nil
        transport = nil
        state = .closing
        if let oldTransport, let sessionID {
            Task { [weak self] in await self?.bestEffortClose(oldTransport, sessionID: sessionID) }
        } else {
            oldTransport?.close()
        }
        state = .disconnected
        statusMessage = "Disconnected."
    }

    func sendInput(_ text: String) async -> Bool {
        guard case let .connected(sessionID) = state, let transport else {
            statusMessage = "Connect before sending input."
            return false
        }
        do {
            try await transport.send(TerminalProtocol.encode(.input(sessionID: sessionID, text: text)))
            return true
        } catch {
            failClosed("Input send failed.")
            return false
        }
    }

    func sendInterrupt() async -> Bool {
        guard case let .connected(sessionID) = state, let transport else {
            statusMessage = "Connect before interrupting."
            return false
        }
        do {
            try await transport.send(TerminalProtocol.encode(.interrupt(sessionID: sessionID)))
            return true
        } catch {
            failClosed("Interrupt send failed.")
            return false
        }
    }

    func clearVisibleHistory() {
        buffer.clear()
        terminalText = ""
        publishToken += 1
        publishTask?.cancel()
        publishTask = nil
    }

    private func receiveLoop(socket: any TerminalTransport, generation loopGeneration: Int) async {
        do {
            while generation == loopGeneration {
                let message = try await socket.receive()
                guard generation == loopGeneration else { return }
                switch try handle(message: message, generation: loopGeneration) {
                case .continueReceiving: continue
                case .terminal: return
                }
            }
        } catch is CancellationError {
            return
        } catch {
            guard generation == loopGeneration else { return }
            failClosed(publicMessage(for: error))
        }
    }

    private func handle(message: TerminalTransportMessage, generation messageGeneration: Int) throws -> HandleResult {
        let data: Data
        switch message {
        case .string(let value): data = Data(value.utf8)
        case .data(let value): data = value
        }
        guard data.count <= maxFrameBytes else {
            failClosed("Terminal output frame exceeded the client limit.")
            return .terminal
        }
        let decoded = try TerminalProtocol.decodeServer(data, expectedSession: currentSessionID)
        switch decoded {
        case .hello(let sessionID):
            guard currentSessionID == nil, transport != nil else { throw ProtocolError.wrongSession }
            state = .connected(sessionID)
            statusMessage = "Connected."
            return .continueReceiving
        case .output(let sessionID, let text):
            guard case let .connected(expected) = state, expected == sessionID else { throw ProtocolError.wrongSession }
            buffer.append(sanitizer.consume(text))
            schedulePublish(for: messageGeneration)
            return .continueReceiving
        case .exit(let sessionID, let code):
            guard case let .connected(expected) = state, expected == sessionID else { throw ProtocolError.wrongSession }
            buffer.append(sanitizer.finish())
            publishImmediately()
            statusMessage = "Process exited with code \(code)."
            generation += 1
            let closingTransport = transport
            transport = nil
            closingTransport?.close()
            state = .disconnected
            return .terminal
        case .error(let sessionID, let code, let message):
            if let currentSessionID, currentSessionID != sessionID { throw ProtocolError.wrongSession }
            failClosed("\(code): \(message)")
            return .terminal
        }
    }

    private var currentSessionID: String? {
        if case let .connected(sessionID) = state { return sessionID }
        return nil
    }

    private func schedulePublish(for loopGeneration: Int) {
        guard publishTask == nil else { return }
        let token = publishToken
        publishTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 50_000_000)
            guard !Task.isCancelled else { return }
            await self?.publishIfCurrent(generation: loopGeneration, token: token)
        }
    }

    private func publishIfCurrent(generation: Int, token: Int) {
        guard self.generation == generation, publishToken == token else { return }
        publishImmediately()
    }

    private func publishImmediately() {
        publishTask?.cancel()
        publishTask = nil
        terminalText = buffer.text
    }

    private func bestEffortClose(_ socket: any TerminalTransport, sessionID: String) async {
        let payload = try? TerminalProtocol.encode(.close(sessionID: sessionID))
        await withTaskGroup(of: Void.self) { group in
            if let payload {
                group.addTask { try? await socket.send(payload) }
            }
            group.addTask {
                try? await Task.sleep(nanoseconds: 150_000_000)
            }
            _ = await group.next()
            group.cancelAll()
        }
        socket.close()
    }

    private func failClosed(_ message: String) {
        publishImmediately()
        generation += 1
        publishToken += 1
        publishTask?.cancel()
        publishTask = nil
        transport?.close()
        transport = nil
        state = .failed(message)
        statusMessage = message
    }

    private func publicMessage(for error: Error) -> String {
        if let protocolError = error as? ProtocolError { return protocolError.localizedDescription }
        return "Terminal connection failed."
    }
}
