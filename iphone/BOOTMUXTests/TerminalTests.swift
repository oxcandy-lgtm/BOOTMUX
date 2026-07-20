import XCTest
@testable import BOOTMUX

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

    func testClientActionSemantics() throws {
        let input = try TerminalProtocol.encode(.input(sessionID: "s", text: "echo BOOTMUX_V0"))
        XCTAssertTrue(input.contains("input_text") && input.contains("echo BOOTMUX_V0"))
        XCTAssertTrue(try TerminalProtocol.encode(.interrupt(sessionID: "s")).contains("interrupt"))
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

    func testStreamingANSISequencesAreRemovedAcrossChunks() {
        var sanitizer = ANSISanitizer()
        XCTAssertEqual(sanitizer.consume("\u{1B}[31"), "")
        XCTAssertEqual(sanitizer.consume("mBOOTMUX"), "BOOTMUX")
        XCTAssertEqual(sanitizer.consume("\u{1B}]0;title"), "")
        XCTAssertEqual(sanitizer.consume("\u{07}日本語"), "日本語")
        XCTAssertFalse(sanitizer.consume("\u{1B}[2J", final: true).contains("\u{1B}"))
    }

    func testCarriageReturnAndControlsAreDeterministic() {
        var sanitizer = ANSISanitizer()
        XCTAssertEqual(sanitizer.consume("a\rb\u{0}c\t\n"), "a\nbc\t\n")
    }
}
