import Foundation

struct ClientMessage: Encodable {
    let v: Int
    let type: String
    let sessionID: String
    let text: String?
    let control: String?

    enum CodingKeys: String, CodingKey {
        case v, type
        case sessionID = "session_id"
        case text, control
    }

    static func input(sessionID: String, text: String) -> ClientMessage {
        ClientMessage(v: 1, type: "input_text", sessionID: sessionID, text: text, control: nil)
    }

    static func interrupt(sessionID: String) -> ClientMessage {
        ClientMessage(v: 1, type: "control", sessionID: sessionID, text: nil, control: "interrupt")
    }

    static func close(sessionID: String) -> ClientMessage {
        ClientMessage(v: 1, type: "close", sessionID: sessionID, text: nil, control: nil)
    }
}

enum ServerMessage {
    case hello(sessionID: String)
    case output(sessionID: String, text: String)
    case exit(sessionID: String, code: Int)
    case error(sessionID: String, code: String, message: String)
}

enum ProtocolError: LocalizedError, Equatable {
    case malformed
    case unsupportedVersion
    case wrongSession
    case unsupportedMessage

    var errorDescription: String? {
        switch self {
        case .malformed: return "Malformed terminal message."
        case .unsupportedVersion: return "Unsupported terminal protocol version."
        case .wrongSession: return "Terminal session mismatch."
        case .unsupportedMessage: return "Unsupported terminal message."
        }
    }
}

enum TerminalProtocol {
    static let version = 1

    static func encode(_ message: ClientMessage) throws -> String {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return String(decoding: try encoder.encode(message), as: UTF8.self)
    }

    static func decodeServer(_ data: Data, expectedSession: String?) throws -> ServerMessage {
        guard let object = try? JSONSerialization.jsonObject(with: data),
              let dictionary = object as? [String: Any],
              let version = dictionary["v"] as? Int,
              let type = dictionary["type"] as? String,
              let sessionID = dictionary["session_id"] as? String else {
            if let object = try? JSONSerialization.jsonObject(with: data),
               let dictionary = object as? [String: Any],
               let version = dictionary["v"] as? Int,
               version != Self.version { throw ProtocolError.unsupportedVersion }
            throw ProtocolError.malformed
        }
        guard version == Self.version else { throw ProtocolError.unsupportedVersion }
        if let expectedSession, sessionID != expectedSession, type != "hello" {
            throw ProtocolError.wrongSession
        }
        switch type {
        case "hello": return .hello(sessionID: sessionID)
        case "output":
            guard dictionary["stream"] as? String == "pty", let text = dictionary["text"] as? String else { throw ProtocolError.malformed }
            return .output(sessionID: sessionID, text: text)
        case "exit":
            guard let code = dictionary["exit_code"] as? Int else { throw ProtocolError.malformed }
            return .exit(sessionID: sessionID, code: code)
        case "error":
            guard let code = dictionary["code"] as? String, let message = dictionary["message"] as? String else { throw ProtocolError.malformed }
            return .error(sessionID: sessionID, code: code, message: message)
        default: throw ProtocolError.unsupportedMessage
        }
    }
}
