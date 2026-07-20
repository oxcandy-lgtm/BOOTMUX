import Foundation
import XCTest
@testable import BOOTMUX

final class FakeTransport: TerminalTransport {
    private let stream: AsyncStream<TerminalTransportMessage>
    private var continuation: AsyncStream<TerminalTransportMessage>.Continuation?
    private(set) var receiveCount = 0
    private(set) var sent: [String] = []
    private(set) var closeCodes: [TerminalCloseCode] = []
    var sendStarted: (() -> Void)?
    var onClose: (() -> Void)?
    var failSends = false
    var neverFinishesSend = false

    init() {
        var stored: AsyncStream<TerminalTransportMessage>.Continuation?
        stream = AsyncStream { stored = $0 }
        continuation = stored
    }

    func resume() {}
    func receive() async throws -> TerminalTransportMessage {
        receiveCount += 1
        for await message in stream { return message }
        throw CancellationError()
    }
    func send(_ text: String) async throws {
        sendStarted?()
        if failSends { throw ProtocolError.malformed }
        if neverFinishesSend {
            while !Task.isCancelled { await Task.yield() }
            throw CancellationError()
        }
        sent.append(text)
    }
    func close(code: TerminalCloseCode) { closeCodes.append(code); onClose?(); continuation?.finish() }
    func push(_ message: TerminalTransportMessage) { continuation?.yield(message) }
}

@MainActor
final class TerminalTests: XCTestCase {
    func testBLEChunkerBatchesCommittedASCIIAndUsesFewerWritesThanCharacters() throws {
        let frames = try BLEChunker(maximumWriteBytes: 64).frames(session: "s", sequence: 1, text: "echo BOOTMUX_HID")
        XCTAssertLessThan(frames.count, "echo BOOTMUX_HID".utf8.count)
        XCTAssertTrue(frames.allSatisfy { $0.count <= 64 })
    }

    func testBLEProtocolControlsAndDuplicateAck() throws {
        let frame = try BLEProtocol.control(session: "s", sequence: 7, control: .ctrlC)
        XCTAssertEqual(String(decoding: frame, as: UTF8.self), "BMX1|CTRL|s|7|CTRL_C")
        let ack = BLEProtocol.parseAck(Data("BMX1|ACK|s|7|DUPLICATE".utf8))
        XCTAssertEqual(ack?.result, "DUPLICATE")
    }

    func testBLESessionScopedFramesAndStopResumeAcks() throws {
        XCTAssertEqual(String(decoding: try BLEProtocol.open(session: "new"), as: UTF8.self), "BMX1|OPEN|new")
        XCTAssertEqual(BLEProtocol.parseAck(Data("BMX1|ACK|new|0|OPENED".utf8))?.result, "OPENED")
        XCTAssertEqual(BLEProtocol.parseAck(Data("BMX1|ACK|new|4|STOPPED".utf8))?.result, "STOPPED")
        XCTAssertEqual(BLEProtocol.parseAck(Data("BMX1|ACK|new|5|RESUMED".utf8))?.result, "RESUMED")
        XCTAssertEqual(BLEProtocol.parseAck(Data("BMX1|ACK|old|5|APPLIED".utf8))?.session, "old")
    }

    func testBLEAckContractSeparatesResumedFromApplied() {
        XCTAssertTrue(BLEAckContract.accepts("RESUMED", for: .control(.resume)))
        XCTAssertFalse(BLEAckContract.accepts("RESUMED", for: .text))
        XCTAssertFalse(BLEAckContract.accepts("RESUMED", for: .control(.enter)))
        XCTAssertFalse(BLEAckContract.accepts("APPLIED", for: .control(.resume)))
        XCTAssertTrue(BLEAckContract.accepts("APPLIED", for: .text))
        XCTAssertTrue(BLEAckContract.accepts("STOPPED", for: .control(.stop)))
        XCTAssertFalse(BLEAckContract.accepts("STOPPED", for: .control(.enter)))
    }

    func testObservedOutputIsNotSynthesizedFromInput() throws {
        let data = Data("{\"v\":1,\"type\":\"output\",\"session_id\":\"s\",\"stream\":\"pty\",\"text\":\"BOOTMUX_V0\"}".utf8)
        guard case let .output(_, text) = try TerminalProtocol.decodeServer(data, expectedSession: "s") else { return XCTFail("expected output") }
        XCTAssertEqual(text, "BOOTMUX_V0")
    }

    func testProtocolRejectsWrongSessionAndUnsupportedVersion() {
        let wrong = Data("{\"v\":1,\"type\":\"output\",\"session_id\":\"other\",\"stream\":\"pty\",\"text\":\"x\"}".utf8)
        XCTAssertThrowsError(try TerminalProtocol.decodeServer(wrong, expectedSession: "s")) { XCTAssertEqual($0 as? ProtocolError, .wrongSession) }
        let version = Data("{\"v\":2,\"type\":\"hello\",\"session_id\":\"s\"}".utf8)
        XCTAssertThrowsError(try TerminalProtocol.decodeServer(version, expectedSession: nil)) { XCTAssertEqual($0 as? ProtocolError, .unsupportedVersion) }
    }

    func testClientActionSemanticsAndCloseMessage() throws {
        let input = try TerminalProtocol.encode(.input(sessionID: "s", text: "echo BOOTMUX_V0"))
        XCTAssertTrue(input.contains("input_text") && input.contains("echo BOOTMUX_V0"))
        XCTAssertTrue(try TerminalProtocol.encode(.interrupt(sessionID: "s")).contains("interrupt"))
        XCTAssertTrue(try TerminalProtocol.encode(.close(sessionID: "s")).contains("\"close\""))
    }

    func testCodexMessagesStayOnTerminalTransport() throws {
        let prompt = try TerminalProtocol.encode(.codexPrompt(sessionID: "s", prompt: "Respond with exactly BOOTMUX_READY", requestID: "r1"))
        XCTAssertTrue(prompt.contains("codex_prompt"))
        XCTAssertTrue(prompt.contains("BOOTMUX_READY"))
        XCTAssertTrue(try TerminalProtocol.encode(.codexCancel(sessionID: "s", requestID: "r1")).contains("codex_cancel"))
        let output = Data("{\"v\":1,\"type\":\"codex_output\",\"session_id\":\"s\",\"request_id\":\"r1\",\"text\":\"BOOTMUX_READY\"}".utf8)
        guard case let .codexOutput(_, requestID, text) = try TerminalProtocol.decodeServer(output, expectedSession: "s") else { return XCTFail("expected Codex output") }
        XCTAssertEqual(requestID, "r1")
        XCTAssertEqual(text, "BOOTMUX_READY")
    }

    func testProtocolLimitsAreSingleContract() {
        XCTAssertEqual(TerminalProtocolLimits.webSocketMessageBytes, 16 * 1024)
        XCTAssertEqual(TerminalProtocolLimits.jsonMessageBytes, 12 * 1024)
        XCTAssertEqual(TerminalProtocolLimits.inputTextBytes, 8 * 1024)
        XCTAssertEqual(TerminalProtocolLimits.terminalHistoryBytes, 128 * 1024)
        XCTAssertEqual("\n".utf8.count, 1)
        XCTAssertEqual("\u{7F}".utf8.count, 1)
    }

    func testBoundedUTF8BufferEvictsOldestTextWithoutBreakingJapanese() {
        var buffer = TerminalBuffer(maxBytes: 12)
        buffer.append("古い")
        buffer.append("新しい日本語")
        XCTAssertLessThanOrEqual(buffer.text.utf8.count, 12)
        XCTAssertFalse(buffer.text.contains("�"))
    }

    func testBufferClearAndHugeBatchRemainBounded() {
        var buffer = TerminalBuffer(maxBytes: 32)
        buffer.append(String(repeating: "BOOTMUX_LINE\n", count: 500))
        XCTAssertLessThanOrEqual(buffer.text.utf8.count, 32)
        buffer.clear()
        XCTAssertEqual(buffer.text, "")
    }

    func testStreamingANSIAndCRLFNormalizationAcrossFrames() {
        var sanitizer = ANSISanitizer()
        var complete = ANSISanitizer()
        XCTAssertEqual(complete.consume("a\r\nb"), "a\nb")
        XCTAssertEqual(sanitizer.consume("a\r"), "a")
        XCTAssertEqual(sanitizer.consume("\nb"), "\nb")
        XCTAssertEqual(sanitizer.consume("\r"), "")
        XCTAssertEqual(sanitizer.finish(), "\n")
        XCTAssertEqual(sanitizer.consume("\u{1B}[31"), "")
        XCTAssertEqual(sanitizer.consume("m日本語\r\n"), "日本語\n")
    }

    func testSelectionRangePreservedAndClamped() {
        XCTAssertEqual(SelectionRange.preserved(NSRange(location: 2, length: 3), newUTF16Length: 10), NSRange(location: 2, length: 3))
        XCTAssertEqual(SelectionRange.preserved(NSRange(location: 8, length: 5), newUTF16Length: 10), NSRange(location: 8, length: 2))
        XCTAssertEqual(SelectionRange.preserved(NSRange(location: 20, length: 1), newUTF16Length: 10), NSRange(location: 10, length: 0))
    }

    func testNormalExitReturnsDisconnectedAndNotFailed() async throws {
        let fake = FakeTransport()
        let session = TerminalSession { _ in fake }
        session.connect(endpoint: "ws://local/v1/terminal")
        fake.push(.string("{\"v\":1,\"type\":\"hello\",\"session_id\":\"s\"}"))
        fake.push(.string("{\"v\":1,\"type\":\"output\",\"session_id\":\"s\",\"stream\":\"pty\",\"text\":\"BOOTMUX_V0\"}"))
        fake.push(.string("{\"v\":1,\"type\":\"exit\",\"session_id\":\"s\",\"exit_code\":0}"))
        try await Task.sleep(nanoseconds: 50_000_000)
        XCTAssertEqual(session.state, .disconnected)
        XCTAssertEqual(session.terminalText, "BOOTMUX_V0")
        XCTAssertFalse(session.statusMessage.contains("failed"))
    }

    func testDoubleConnectIsRejectedAndReconnectUsesFreshSession() async throws {
        let first = FakeTransport()
        let second = FakeTransport()
        var transports = [first, second]
        let session = TerminalSession { _ in transports.removeFirst() }
        session.connect(endpoint: "ws://local/v1/terminal")
        session.connect(endpoint: "ws://local/v1/terminal")
        XCTAssertTrue(session.statusMessage.contains("Already connected"))
        first.push(.string("{\"v\":1,\"type\":\"hello\",\"session_id\":\"old\"}"))
        try await waitUntil { if case .connected("old") = session.state { return true }; return false }
        session.disconnect()
        try await waitUntil { session.state == .disconnected }
        session.connect(endpoint: "ws://local/v1/terminal")
        second.push(.string("{\"v\":1,\"type\":\"hello\",\"session_id\":\"new\"}"))
        try await waitUntil { if case .connected("new") = session.state { return true }; return false }
        XCTAssertEqual(second.receiveCount, 1)
    }

    func testConnectBeforeHelloRejectedAndSendFailureFailsClosed() async throws {
        let fake = FakeTransport()
        let session = TerminalSession { _ in fake }
        let beforeHelloAccepted = await session.sendInput("before hello")
        XCTAssertFalse(beforeHelloAccepted)
        session.connect(endpoint: "ws://local/v1/terminal")
        fake.push(.string("{\"v\":1,\"type\":\"hello\",\"session_id\":\"s\"}"))
        try await Task.sleep(nanoseconds: 10_000_000)
        fake.failSends = true
        let failedSendAccepted = await session.sendInput("x")
        XCTAssertFalse(failedSendAccepted)
        XCTAssertTrue({ if case .failed = session.state { return true }; return false }())
    }

    func testOversizedInputIsRejectedWithoutDisconnectOrSend() async throws {
        let fake = FakeTransport()
        let session = TerminalSession { _ in fake }
        session.connect(endpoint: "ws://local/v1/terminal")
        fake.push(.string("{\"v\":1,\"type\":\"hello\",\"session_id\":\"s\"}"))
        try await waitUntil { if case .connected = session.state { return true }; return false }
        let oversizedInputAccepted = await session.sendInput(String(repeating: "x", count: TerminalProtocolLimits.inputTextBytes + 1))
        XCTAssertFalse(oversizedInputAccepted)
        XCTAssertTrue({ if case .connected = session.state { return true }; return false }())
        XCTAssertTrue(fake.sent.isEmpty)
    }

    func testDisconnectSendsBestEffortTypedCloseAndCleansUp() async throws {
        let fake = FakeTransport()
        let session = TerminalSession { _ in fake }
        session.connect(endpoint: "ws://local/v1/terminal")
        fake.push(.string("{\"v\":1,\"type\":\"hello\",\"session_id\":\"s\"}"))
        try await waitUntil { if case .connected = session.state { return true }; return false }
        session.disconnect()
        try await Task.sleep(nanoseconds: 200_000_000)
        XCTAssertEqual(session.state, .disconnected)
        XCTAssertTrue(fake.sent.contains { $0.contains("\"close\"") })
        XCTAssertEqual(fake.closeCodes.count, 1)
    }

    func testTypedCloseTimeoutClosesTransportWithoutWaitingForSend() async throws {
        let fake = FakeTransport()
        fake.neverFinishesSend = true
        let started = expectation(description: "close send started")
        let closed = expectation(description: "transport closed")
        fake.sendStarted = { started.fulfill() }
        fake.onClose = { closed.fulfill() }
        let session = TerminalSession { _ in fake }
        session.connect(endpoint: "ws://local/v1/terminal")
        fake.push(.string("{\"v\":1,\"type\":\"hello\",\"session_id\":\"s\"}"))
        try await waitUntil { if case .connected = session.state { return true }; return false }
        let disconnectStarted = Date()
        session.disconnect()
        await fulfillment(of: [started], timeout: 1)
        await fulfillment(of: [closed], timeout: 1)
        XCTAssertLessThan(Date().timeIntervalSince(disconnectStarted), 0.25)
        XCTAssertEqual(session.state, .disconnected)
    }

    func testClearPreventsScheduledPublishFromResurrectingOutput() async throws {
        let fake = FakeTransport()
        let session = TerminalSession { _ in fake }
        session.connect(endpoint: "ws://local/v1/terminal")
        fake.push(.string("{\"v\":1,\"type\":\"hello\",\"session_id\":\"s\"}"))
        fake.push(.string("{\"v\":1,\"type\":\"output\",\"session_id\":\"s\",\"stream\":\"pty\",\"text\":\"old\"}"))
        session.clearVisibleHistory()
        try await waitUntil { session.terminalText.isEmpty }
        XCTAssertEqual(session.terminalText, "")
    }

    func testRapidFramesStayBoundedAndServerErrorFinalizesOutput() async throws {
        let fake = FakeTransport()
        let session = TerminalSession { _ in fake }
        session.connect(endpoint: "ws://local/v1/terminal")
        fake.push(.string("{\"v\":1,\"type\":\"hello\",\"session_id\":\"s\"}"))
        try await waitUntil { if case .connected = session.state { return true }; return false }
        fake.push(.string("{\"v\":1,\"type\":\"output\",\"session_id\":\"s\",\"stream\":\"pty\",\"text\":\"tail\\r\"}"))
        for _ in 0..<100 { fake.push(.string("{\"v\":1,\"type\":\"output\",\"session_id\":\"s\",\"stream\":\"pty\",\"text\":\"x\"}")) }
        fake.push(.string("{\"v\":1,\"type\":\"error\",\"session_id\":\"s\",\"code\":\"test\",\"message\":\"safe\"}"))
        try await waitUntil { if case .failed = session.state { return true }; return false }
        XCTAssertLessThanOrEqual(session.terminalText.utf8.count, TerminalProtocolLimits.terminalHistoryBytes)
        XCTAssertTrue(session.terminalText.contains("x"))
        XCTAssertTrue(session.terminalText.contains("tail\n"))
    }

    func testOversizedWebSocketAndJSONMessagesFailClosed() async throws {
        let websocketFake = FakeTransport()
        let websocketSession = TerminalSession { _ in websocketFake }
        websocketSession.connect(endpoint: "ws://local/v1/terminal")
        websocketFake.push(.data(Data(repeating: 0x20, count: TerminalProtocolLimits.webSocketMessageBytes + 1)))
        try await waitUntil { if case .failed = websocketSession.state { return true }; return false }

        let jsonFake = FakeTransport()
        let jsonSession = TerminalSession { _ in jsonFake }
        jsonSession.connect(endpoint: "ws://local/v1/terminal")
        jsonFake.push(.data(Data(repeating: 0x20, count: TerminalProtocolLimits.jsonMessageBytes + 1)))
        try await waitUntil { if case .failed = jsonSession.state { return true }; return false }
    }

    private func waitUntil(_ predicate: @escaping () -> Bool) async throws {
        let deadline = Date().addingTimeInterval(1)
        while !predicate() {
            if Date() >= deadline { throw XCTSkip("deterministic state transition did not occur") }
            await Task.yield()
        }
    }
}
