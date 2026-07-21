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

    func wifiFrames(session: String, sequence: UInt32, payload: String) throws -> [Data] {
        let bytes = Array(payload.utf8)
        guard !bytes.isEmpty else { throw BLEProtocolError.oversizedWiFiPayload }
        var chunks: [String] = []
        var offset = 0
        while offset < bytes.count {
            var low = 1
            var high = bytes.count - offset
            var best = 0
            while low <= high {
                let mid = (low + high) / 2
                let candidate = String(decoding: bytes[offset..<(offset + mid)], as: UTF8.self)
                do {
                    // Size against the largest legal frame header. The actual
                    // part/total values can only make a final frame shorter.
                    let frame = try BLEProtocol.wifiProvision(session: session, sequence: sequence, part: 15, total: 16, payload: candidate)
                    if frame.count <= maximumWriteBytes { best = mid; low = mid + 1 } else { high = mid - 1 }
                } catch { high = mid - 1 }
            }
            guard best > 0 else { throw BLEProtocolError.oversizedWiFiPayload }
            chunks.append(String(decoding: bytes[offset..<(offset + best)], as: UTF8.self))
            offset += best
        }
        guard chunks.count <= 16 else { throw BLEProtocolError.tooManyParts }
        return try chunks.enumerated().map { index, chunk in
            try BLEProtocol.wifiProvision(session: session, sequence: sequence, part: index, total: chunks.count, payload: chunk)
        }
    }
}
