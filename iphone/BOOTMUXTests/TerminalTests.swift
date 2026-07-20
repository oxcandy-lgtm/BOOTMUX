import Foundation
import XCTest
@testable import BOOTMUX

final class FakeTransport: TerminalTransport {
    private let stream: AsyncStream<TerminalTransportMessage>
    private var continuation: AsyncStream<TerminalTransportMessage>.Continuation?
    private(set) var sent: [String] = []
    var failSends = false

    init() {
        var stored: AsyncStream<TerminalTransportMessage>.Continuation?
        stream = AsyncStream { stored = $0 }
        continuation = stored
    }

    func resume() {}
    func receive() async throws -> TerminalTransportMessage {
        for await message in stream { return message }
        throw CancellationError()
    }
    func send(_ text: String) async throws {
        if failSends { throw ProtocolError.malformed }
        sent.append(text)
    }
    func close() { continuation?.finish() }
    func push(_ message: TerminalTransportMessage) { continuation?.yield(message) }
}

@MainActor
final class TerminalTests: XCTestCase {
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
        XCTAssertEqual(sanitizer.consume("a\r"), "a")
        XCTAssertEqual(sanitizer.consume("\nb"), "\nb")
        XCTAssertEqual(sanitizer.consume("\r"), "")
        XCTAssertEqual(sanitizer.finish(), "\n")
        XCTAssertEqual(sanitizer.consume("\u{1B}[31"), "")
        XCTAssertEqual(sanitizer.consume("m日本語\r\n"), "日本語\n")
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

    func testConnectBeforeHelloRejectedAndSendFailureFailsClosed() async throws {
        let fake = FakeTransport()
        let session = TerminalSession { _ in fake }
        XCTAssertFalse(await session.sendInput("before hello"))
        session.connect(endpoint: "ws://local/v1/terminal")
        fake.push(.string("{\"v\":1,\"type\":\"hello\",\"session_id\":\"s\"}"))
        try await Task.sleep(nanoseconds: 10_000_000)
        fake.failSends = true
        XCTAssertFalse(await session.sendInput("x"))
        XCTAssertTrue({ if case .failed = session.state { return true }; return false }())
    }

    func testDisconnectSendsBestEffortTypedCloseAndCleansUp() async throws {
        let fake = FakeTransport()
        let session = TerminalSession { _ in fake }
        session.connect(endpoint: "ws://local/v1/terminal")
        fake.push(.string("{\"v\":1,\"type\":\"hello\",\"session_id\":\"s\"}"))
        try await Task.sleep(nanoseconds: 10_000_000)
        session.disconnect()
        try await Task.sleep(nanoseconds: 200_000_000)
        XCTAssertEqual(session.state, .disconnected)
        XCTAssertTrue(fake.sent.contains { $0.contains("\"close\"") })
    }

    func testClearPreventsScheduledPublishFromResurrectingOutput() async throws {
        let fake = FakeTransport()
        let session = TerminalSession { _ in fake }
        session.connect(endpoint: "ws://local/v1/terminal")
        fake.push(.string("{\"v\":1,\"type\":\"hello\",\"session_id\":\"s\"}"))
        fake.push(.string("{\"v\":1,\"type\":\"output\",\"session_id\":\"s\",\"stream\":\"pty\",\"text\":\"old\"}"))
        session.clearVisibleHistory()
        try await Task.sleep(nanoseconds: 100_000_000)
        XCTAssertEqual(session.terminalText, "")
    }
}
