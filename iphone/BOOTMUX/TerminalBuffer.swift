import Foundation

struct TerminalBuffer {
    let maxBytes: Int
    private(set) var text = ""

    init(maxBytes: Int = 131_072) {
        precondition(maxBytes > 0)
        self.maxBytes = maxBytes
    }

    mutating func append(_ observedOutput: String) {
        var bytes = Array(text.utf8)
        bytes.append(contentsOf: observedOutput.utf8)
        guard bytes.count > maxBytes else {
            text = String(decoding: bytes, as: UTF8.self)
            return
        }
        var start = bytes.count - maxBytes
        while start < bytes.count && (bytes[start] & 0xC0) == 0x80 { start += 1 }
        text = String(decoding: bytes[start...], as: UTF8.self)
    }

    mutating func clear() { text = "" }
}
