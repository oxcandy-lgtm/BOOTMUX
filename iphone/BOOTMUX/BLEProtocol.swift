import Foundation

enum BLEProtocolError: Error, Equatable {
    case nonASCII
    case emptySession
    case oversizedText
    case tooManyParts
    case malformedAck
}

enum BLEControl: String {
    case enter = "ENTER"
    case backspace = "BACKSPACE"
    case ctrlC = "CTRL_C"
    case stop = "STOP"
    case resume = "RESUME"
}

enum BLEOperationKind {
    case text
    case control(BLEControl)
}

enum BLEAckContract {
    static func accepts(_ result: String, for operation: BLEOperationKind) -> Bool {
        switch result {
        case "RESUMED":
            if case .control(.resume) = operation { return true }
            return false
        case "STOPPED":
            if case .control(.stop) = operation { return true }
            return false
        case "APPLIED", "DUPLICATE":
            if case .control(.resume) = operation { return false }
            return true
        default:
            return false
        }
    }
}

enum BLEProtocol {
    static let serviceUUID = "7C1B0001-4B4F-4D55-9A01-42584D583101"
    static let rxUUID = "7C1B0002-4B4F-4D55-9A01-42584D583101"
    static let txUUID = "7C1B0003-4B4F-4D55-9A01-42584D583101"
    static let maximumCommittedBytes = 512
    static let maximumParts = 32

    static func escape(_ value: String) -> String {
        value.replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "|", with: "\\|")
            .replacingOccurrences(of: "\n", with: "\\n")
            .replacingOccurrences(of: "\r", with: "\\r")
    }

    static func open(session: String) throws -> Data {
        try frame(["BMX1", "OPEN", validSession(session)])
    }

    static func text(session: String, sequence: UInt32, part: Int, total: Int, payload: String) throws -> Data {
        guard total > 0, total <= maximumParts, part >= 0, part < total else { throw BLEProtocolError.tooManyParts }
        return try frame(["BMX1", "TEXT", validSession(session), String(sequence), String(part), String(total), escape(payload)])
    }

    static func control(session: String, sequence: UInt32, control: BLEControl) throws -> Data {
        try frame(["BMX1", "CTRL", validSession(session), String(sequence), control.rawValue])
    }

    static func parseAck(_ data: Data) -> (session: String, sequence: UInt32, result: String)? {
        guard let value = String(data: data, encoding: .utf8) else { return nil }
        let fields = value.split(separator: "|", omittingEmptySubsequences: false)
        guard fields.count == 5, fields[0] == "BMX1", fields[1] == "ACK", let sequence = UInt32(fields[3]) else { return nil }
        return (String(fields[2]), sequence, String(fields[4]))
    }

    private static func validSession(_ value: String) throws -> String {
        guard !value.isEmpty, !value.contains("|"), !value.contains("\\") else { throw BLEProtocolError.emptySession }
        return value
    }

    private static func frame(_ fields: [String]) throws -> Data {
        let value = fields.joined(separator: "|")
        guard value.utf8.count <= maximumCommittedBytes else { throw BLEProtocolError.oversizedText }
        return Data(value.utf8)
    }
}
