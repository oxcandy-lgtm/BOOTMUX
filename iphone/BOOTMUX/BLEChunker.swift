import Foundation

struct BLEChunker {
    let maximumWriteBytes: Int

    func frames(session: String, sequence: UInt32, text: String) throws -> [Data] {
        guard text.utf8.allSatisfy({ $0 >= 0x20 && $0 <= 0x7E || $0 == 0x0A || $0 == 0x0D }) else { throw BLEProtocolError.nonASCII }
        guard text.utf8.count <= BLEProtocol.maximumCommittedBytes else { throw BLEProtocolError.oversizedText }
        let characters = Array(text)
        var chunks: [String] = []
        var current = ""
        for character in characters {
            let candidate = current + String(character)
            let escapedBytes = BLEProtocol.escape(candidate).utf8.count
            let overhead = 32 + session.utf8.count + String(sequence).count + 8
            if !current.isEmpty && escapedBytes + overhead > maximumWriteBytes {
                chunks.append(current)
                current = String(character)
            } else {
                current = candidate
            }
        }
        if !current.isEmpty || text.isEmpty { chunks.append(current) }
        guard chunks.count <= BLEProtocol.maximumParts else { throw BLEProtocolError.tooManyParts }
        return try chunks.enumerated().map { index, chunk in
            try BLEProtocol.text(session: session, sequence: sequence, part: index, total: chunks.count, payload: chunk)
        }
    }
}
