import Foundation

enum SelectionRange {
    static func preserved(_ old: NSRange, newUTF16Length: Int) -> NSRange {
        let location = min(max(old.location, 0), newUTF16Length)
        let oldEnd = min(max(old.location + old.length, 0), newUTF16Length)
        return NSRange(location: location, length: max(0, oldEnd - location))
    }
}
