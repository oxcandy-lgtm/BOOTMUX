import Foundation

enum CodexRecoveryArtifacts {
    static let maxURLBytes = 2 * 1024
    static let maxDeviceCodeBytes = 128

    static func extractHTTPSURL(from text: String) -> URL? {
        let pattern = #"https://[^\s<>\"']+"#
        guard let expression = try? NSRegularExpression(pattern: pattern) else { return nil }
        let range = NSRange(text.startIndex..., in: text)
        for match in expression.matches(in: text, range: range).reversed() {
            guard let matchRange = Range(match.range, in: text) else { continue }
            var candidate = String(text[matchRange])
            while candidate.last.map({ ".,);]".contains($0) }) == true { candidate.removeLast() }
            guard candidate.utf8.count <= maxURLBytes, let url = URL(string: candidate),
                  url.scheme?.lowercased() == "https", url.host != nil,
                  url.user == nil, url.password == nil,
                  !candidate.unicodeScalars.contains(where: { $0.value < 0x20 || $0.value == 0x7f }) else { continue }
            return url
        }
        return nil
    }

    static func extractDeviceCode(from text: String) -> String? {
        let pattern = #"(?i)(?:device\s+code|code)\s*[:=]?\s*([A-Z0-9]{4,8}(?:-[A-Z0-9]{4,8}){1,3})\b"#
        guard let expression = try? NSRegularExpression(pattern: pattern) else { return nil }
        let range = NSRange(text.startIndex..., in: text)
        for match in expression.matches(in: text, range: range).reversed() {
            guard match.numberOfRanges > 1, let codeRange = Range(match.range(at: 1), in: text) else { continue }
            let code = String(text[codeRange]).uppercased()
            if code.utf8.count <= maxDeviceCodeBytes { return code }
        }
        return nil
    }
}

enum TerminalProtocolLimits {
    static let webSocketMessageBytes = 16 * 1024
    static let jsonMessageBytes = 12 * 1024
    static let inputTextBytes = 8 * 1024
    static let terminalHistoryBytes = 128 * 1024
}

enum TerminalCloseCode {
    case normal
    case goingAway
}

struct ClientMessage: Encodable {
    let v: Int
    let type: String
    let sessionID: String
    let text: String?
    let control: String?
    let prompt: String?
    let requestID: String?

    enum CodingKeys: String, CodingKey {
        case v, type
        case sessionID = "session_id"
        case text, control, prompt
        case requestID = "request_id"
    }

    static func input(sessionID: String, text: String) -> ClientMessage {
        ClientMessage(v: 1, type: "input_text", sessionID: sessionID, text: text, control: nil, prompt: nil, requestID: nil)
    }

    static func interrupt(sessionID: String) -> ClientMessage {
        ClientMessage(v: 1, type: "control", sessionID: sessionID, text: nil, control: "interrupt", prompt: nil, requestID: nil)
    }

    static func close(sessionID: String) -> ClientMessage {
        ClientMessage(v: 1, type: "close", sessionID: sessionID, text: nil, control: nil, prompt: nil, requestID: nil)
    }

    static func codexPrompt(sessionID: String, prompt: String, requestID: String) -> ClientMessage {
        ClientMessage(v: 1, type: "codex_prompt", sessionID: sessionID, text: nil, control: nil, prompt: prompt, requestID: requestID)
    }

    static func codexCancel(sessionID: String, requestID: String) -> ClientMessage {
        ClientMessage(v: 1, type: "codex_cancel", sessionID: sessionID, text: nil, control: nil, prompt: nil, requestID: requestID)
    }

    static func codexNewSession(sessionID: String) -> ClientMessage {
        ClientMessage(v: 1, type: "codex_new_session", sessionID: sessionID, text: nil, control: nil, prompt: nil, requestID: nil)
    }
}

enum ServerMessage {
    case hello(sessionID: String)
    case mirrorHello(sessionID: String)
    case output(sessionID: String, text: String)
    case mirrorOutput(sessionID: String, text: String)
    case exit(sessionID: String, code: Int)
    case error(sessionID: String, code: String, message: String)
    case mirrorError(sessionID: String, code: String, message: String)
    case codexStarted(sessionID: String, requestID: String)
    case codexOutput(sessionID: String, requestID: String, text: String)
    case codexExit(sessionID: String, requestID: String, code: Int)
    case codexError(sessionID: String, requestID: String, code: String, message: String)
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
        case "mirror_hello": return .mirrorHello(sessionID: sessionID)
        case "output":
            guard dictionary["stream"] as? String == "pty", let text = dictionary["text"] as? String else { throw ProtocolError.malformed }
            return .output(sessionID: sessionID, text: text)
        case "mirror_output":
            guard dictionary["stream"] as? String == "hid_mirror", let text = dictionary["text"] as? String else { throw ProtocolError.malformed }
            return .mirrorOutput(sessionID: sessionID, text: text)
        case "exit":
            guard let code = dictionary["exit_code"] as? Int else { throw ProtocolError.malformed }
            return .exit(sessionID: sessionID, code: code)
        case "error":
            guard let code = dictionary["code"] as? String, let message = dictionary["message"] as? String else { throw ProtocolError.malformed }
            return .error(sessionID: sessionID, code: code, message: message)
        case "mirror_error":
            guard dictionary["stream"] as? String == "hid_mirror",
                  let code = dictionary["code"] as? String,
                  let message = dictionary["message"] as? String else { throw ProtocolError.malformed }
            return .mirrorError(sessionID: sessionID, code: code, message: message)
        case "codex_started":
            guard let requestID = dictionary["request_id"] as? String else { throw ProtocolError.malformed }
            return .codexStarted(sessionID: sessionID, requestID: requestID)
        case "codex_output":
            guard let requestID = dictionary["request_id"] as? String, let text = dictionary["text"] as? String else { throw ProtocolError.malformed }
            return .codexOutput(sessionID: sessionID, requestID: requestID, text: text)
        case "codex_exit":
            guard let requestID = dictionary["request_id"] as? String, let code = dictionary["exit_code"] as? Int else { throw ProtocolError.malformed }
            return .codexExit(sessionID: sessionID, requestID: requestID, code: code)
        case "codex_error":
            guard let requestID = dictionary["request_id"] as? String, let code = dictionary["code"] as? String, let message = dictionary["message"] as? String else { throw ProtocolError.malformed }
            return .codexError(sessionID: sessionID, requestID: requestID, code: code, message: message)
        default: throw ProtocolError.unsupportedMessage
        }
    }
}
