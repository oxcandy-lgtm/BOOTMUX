import SwiftUI
import UIKit

struct SelectableTerminalView: UIViewRepresentable {
    let text: String

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
        view.text = text
        view.selectedRange = SelectionRange.preserved(selected, newUTF16Length: view.text.utf16.count)
        let maxX = max(0, view.contentSize.width - view.bounds.width + view.adjustedContentInset.right)
        let maxY = max(0, view.contentSize.height - view.bounds.height + view.adjustedContentInset.bottom)
        view.setContentOffset(CGPoint(x: min(max(0, offset.x), maxX), y: min(max(0, offset.y), maxY)), animated: false)
    }
}
