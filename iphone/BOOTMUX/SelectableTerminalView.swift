import SwiftUI
import UIKit

enum TerminalFollowPolicy {
    static func shouldFollow(enabled: Bool, nearBottom: Bool, hasSelection: Bool) -> Bool {
        enabled && nearBottom && !hasSelection
    }
}

struct SelectableTerminalView: UIViewRepresentable {
    let text: String
    let follow: Bool
    let scrollToken: Int

    func makeUIView(context: Context) -> UITextView {
        let view = UITextView()
        view.isEditable = false
        view.isSelectable = true
        view.dataDetectorTypes = []
        view.backgroundColor = .clear
        view.font = UIFont.monospacedSystemFont(ofSize: 14, weight: .regular)
        view.textContainerInset = UIEdgeInsets(top: 8, left: 8, bottom: 8, right: 8)
        return view
    }

    func updateUIView(_ view: UITextView, context: Context) {
        guard view.text != text else { return }
        let selected = view.selectedRange
        let offset = view.contentOffset
        let wasNearBottom = offset.y + view.bounds.height >= view.contentSize.height - 36
        let hadSelection = selected.length > 0
        view.text = text
        view.selectedRange = SelectionRange.preserved(selected, newUTF16Length: view.text.utf16.count)
        let maxX = max(0, view.contentSize.width - view.bounds.width + view.adjustedContentInset.right)
        let maxY = max(0, view.contentSize.height - view.bounds.height + view.adjustedContentInset.bottom)
        let shouldFollow = TerminalFollowPolicy.shouldFollow(enabled: follow, nearBottom: wasNearBottom, hasSelection: hadSelection)
        let targetY = shouldFollow ? maxY : min(max(0, offset.y), maxY)
        view.setContentOffset(CGPoint(x: min(max(0, offset.x), maxX), y: targetY), animated: false)
    }
}
