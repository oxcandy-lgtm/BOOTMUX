import Foundation

struct ANSISanitizer {
    private enum State { case normal, escape, csi, osc, oscEscape }
    private var state: State = .normal
    private var pendingCR = false

    mutating func consume(_ input: String, final: Bool = false) -> String {
        var output = String()
        for scalar in input.unicodeScalars {
            let value = scalar.value
            if state == .normal, pendingCR {
                if value == 0x0A {
                    output.append("\n")
                    pendingCR = false
                    continue
                }
                output.append("\n")
                pendingCR = false
            }
            switch state {
            case .normal:
                if value == 0x1B { state = .escape }
                else if value == 0x00 || (value < 0x20 && value != 0x09 && value != 0x0A && value != 0x0D) { continue }
                else if value == 0x0D { pendingCR = true }
                else { output.unicodeScalars.append(scalar) }
            case .escape:
                if value == 0x5B { state = .csi }
                else if value == 0x5D { state = .osc }
                else { state = .normal }
            case .csi:
                if (0x40...0x7E).contains(value) { state = .normal }
            case .osc:
                if value == 0x07 { state = .normal }
                else if value == 0x1B { state = .oscEscape }
            case .oscEscape:
                state = value == 0x5C ? .normal : .osc
            }
        }
        if final {
            if pendingCR { output.append("\n") }
            pendingCR = false
            state = .normal
        }
        return output
    }

    mutating func finish() -> String { consume("", final: true) }
}
