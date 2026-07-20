import SwiftUI

struct ContentView: View {
    @StateObject private var session = TerminalSession()
    @State private var endpoint = "ws://127.0.0.1:8765/v1/terminal"
    @State private var command = ""

    var body: some View {
        VStack(spacing: 10) {
            HStack {
                Text("BOOTMUX").font(.headline)
                Spacer()
                Text("TERMINAL: \(session.state.label)").font(.caption.monospaced())
            }.padding(.horizontal)
            SelectableTerminalView(text: session.terminalText)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(.secondary.opacity(0.3)))
            Text(session.statusMessage).font(.caption).foregroundStyle(.secondary)
            TextField("WebSocket endpoint", text: $endpoint)
                .textInputAutocapitalization(.never).autocorrectionDisabled().textFieldStyle(.roundedBorder)
            TextField("Command input", text: $command, axis: .vertical)
                .textInputAutocapitalization(.never).autocorrectionDisabled().textFieldStyle(.roundedBorder)
            HStack {
                Button("CONNECT") { session.connect(endpoint: endpoint) }
                Button("DISCONNECT") { session.disconnect() }
                Button("SEND") {
                    let value = command
                    Task { if await session.sendInput(value) { command = "" } }
                }
                Button("ENTER") { Task { _ = await session.sendInput("\n") } }
                Button("BACKSPACE") { Task { _ = await session.sendInput("\u{7F}") } }
            }
            HStack {
                Button("CTRL-C") { Task { _ = await session.sendInterrupt() } }
                Button("CLEAR") { session.clearVisibleHistory() }
            }
        }.padding()
    }
}
