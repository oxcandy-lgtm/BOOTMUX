import Foundation
import SwiftUI

@MainActor
final class TerminalSession: ObservableObject {
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

    private var task: URLSessionWebSocketTask?
    private var generation = 0
    private var buffer = TerminalBuffer()
    private var sanitizer = ANSISanitizer()
    private var pendingOutput = ""
    private var flushTask: Task<Void, Never>?

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
        buffer.clear()
        terminalText = ""
        pendingOutput = ""
        sanitizer = ANSISanitizer()
        state = .connecting
        statusMessage = "Connecting."
        let socket = URLSession.shared.webSocketTask(with: url)
        task = socket
        socket.resume()
        Task { [weak self, weak socket] in
            guard let self, let socket else { return }
            await self.receiveLoop(socket: socket, generation: currentGeneration)
        }
    }

    func disconnect() {
        guard task != nil else { state = .disconnected; return }
        generation += 1
        state = .closing
        flushTask?.cancel()
        flushTask = nil
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
        pendingOutput = ""
        state = .disconnected
        statusMessage = "Disconnected."
    }

    func sendInput(_ text: String) async -> Bool {
        guard case let .connected(sessionID) = state, let task else {
            statusMessage = "Connect before sending input."
            return false
        }
        do {
            try await task.send(.string(TerminalProtocol.encode(.input(sessionID: sessionID, text: text))))
            return true
        } catch {
            failClosed("Input send failed.")
            return false
        }
    }

    func sendInterrupt() async -> Bool {
        guard case let .connected(sessionID) = state, let task else {
            statusMessage = "Connect before interrupting."
            return false
        }
        do {
            try await task.send(.string(TerminalProtocol.encode(.interrupt(sessionID: sessionID))))
            return true
        } catch {
            failClosed("Interrupt send failed.")
            return false
        }
    }

    func clearVisibleHistory() {
        buffer.clear()
        terminalText = ""
    }

    private func receiveLoop(socket: URLSessionWebSocketTask, generation loopGeneration: Int) async {
        do {
            while generation == loopGeneration {
                let message = try await socket.receive()
                guard generation == loopGeneration else { return }
                let data: Data
                switch message {
                case .string(let value): data = Data(value.utf8)
                case .data(let value): data = value
                @unknown default: throw ProtocolError.malformed
                }
                try handle(data: data, generation: loopGeneration)
            }
        } catch is CancellationError {
            return
        } catch {
            guard generation == loopGeneration else { return }
            failClosed(publicMessage(for: error))
        }
    }

    private func handle(data: Data, generation messageGeneration: Int) throws {
        let message = try TerminalProtocol.decodeServer(data, expectedSession: currentSessionID)
        switch message {
        case .hello(let sessionID):
            guard currentSessionID == nil, task != nil else { throw ProtocolError.wrongSession }
            state = .connected(sessionID)
            statusMessage = "Connected."
        case .output(let sessionID, let text):
            guard case let .connected(expected) = state, expected == sessionID else { throw ProtocolError.wrongSession }
            pendingOutput += sanitizer.consume(text)
            scheduleFlush(for: messageGeneration)
        case .exit(let sessionID, let code):
            guard case let .connected(expected) = state, expected == sessionID else { throw ProtocolError.wrongSession }
            flushPending()
            statusMessage = "Process exited with code \(code)."
            task?.cancel(with: .normalClosure, reason: nil)
            task = nil
            state = .disconnected
        case .error(let sessionID, let code, let message):
            if let currentSessionID, currentSessionID != sessionID { throw ProtocolError.wrongSession }
            failClosed("\(code): \(message)")
        }
    }

    private var currentSessionID: String? {
        if case let .connected(sessionID) = state { return sessionID }
        return nil
    }

    private func scheduleFlush(for loopGeneration: Int) {
        guard flushTask == nil else { return }
        flushTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 50_000_000)
            guard !Task.isCancelled else { return }
            await MainActor.run {
                guard let self, self.generation == loopGeneration else { return }
                self.flushPending()
            }
        }
    }

    private func flushPending() {
        flushTask = nil
        guard !pendingOutput.isEmpty else { return }
        buffer.append(pendingOutput)
        pendingOutput = ""
        terminalText = buffer.text
    }

    private func failClosed(_ message: String) {
        generation += 1
        flushTask?.cancel()
        flushTask = nil
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
        pendingOutput = ""
        state = .failed(message)
        statusMessage = message
    }

    private func publicMessage(for error: Error) -> String {
        if let protocolError = error as? ProtocolError { return protocolError.localizedDescription }
        return "Terminal connection failed."
    }
}
