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
        view.selectedRange = NSRange(location: min(selected.location, view.text.utf16.count), length: 0)
        view.setContentOffset(offset, animated: false)
    }
}
