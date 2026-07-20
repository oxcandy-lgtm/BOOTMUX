import SwiftUI

enum BOOTMUXScenePhasePolicy {
    static func disconnects(for phase: ScenePhase) -> Bool {
        phase == .background
    }
}

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var session = TerminalSession()
    @StateObject private var ble = BLEBridgeSession()
    @State private var endpoint = "ws://127.0.0.1:8765/v1/terminal"
    @State private var command = ""
    @State private var codexPrompt = ""
    @State private var codexMode = false
    @State private var showSettings = false
    @State private var showDiagnostics = false
    @FocusState private var focusedField: InputField?

    private enum InputField { case command, endpoint }

    var body: some View {
        GeometryReader { proxy in
            VStack(spacing: 8) {
                compactHeader
                Picker("Mode", selection: $codexMode) {
                    Text("TERMINAL").tag(false)
                    Text("CODEX").tag(true)
                }
                .pickerStyle(.segmented)
                SelectableTerminalView(text: session.terminalText)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .layoutPriority(10)
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(.secondary.opacity(0.3)))
                Text(session.statusMessage)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .leading)
                if codexMode {
                    codexComposer
                } else {
                    commandComposer
                    essentialControls
                }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 8)
            .frame(width: proxy.size.width, height: proxy.size.height, alignment: .top)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .sheet(isPresented: $showSettings) { settingsSheet }
        .sheet(isPresented: $showDiagnostics) { diagnosticsSheet }
        .scrollDismissesKeyboard(.interactively)
        .toolbar {
            ToolbarItemGroup(placement: .keyboard) {
                Spacer()
                Button("Done") { focusedField = nil }
            }
        }
        .onChange(of: scenePhase) { _, phase in
            ble.recordLifecycle(String(describing: phase))
            if BOOTMUXScenePhasePolicy.disconnects(for: phase) {
                session.disconnect()
                ble.disconnect()
            }
        }
    }

    private var compactHeader: some View {
        HStack(spacing: 8) {
            Text("BOOTMUX")
                .font(.headline)
                .lineLimit(1)
            Spacer(minLength: 4)
            Text("BLE \(ble.state.uiLabel)")
                .font(.caption2.monospaced())
                .lineLimit(1)
            Text("TERM \(session.state.label)")
                .font(.caption2.monospaced())
                .lineLimit(1)
            Text("CODEX \(session.codexState)")
                .font(.caption2.monospaced())
                .lineLimit(1)
            Button("SETTINGS") { showSettings = true }
                .font(.caption2)
                .lineLimit(1)
            Button("LOG") { showDiagnostics = true }
                .font(.caption2)
                .lineLimit(1)
        }
        .frame(minHeight: 44)
    }

    private var commandComposer: some View {
        TextField("Command input", text: $command, axis: .vertical)
            .focused($focusedField, equals: .command)
            .lineLimit(1...4)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .textFieldStyle(.roundedBorder)
            .frame(minHeight: 44, maxHeight: 100)
    }

    private var essentialControls: some View {
        let controls: [(String, () -> Void)] = focusedField == .command
            ? [("HID SEND", sendHID), ("ENTER", sendHIDEnter)]
            : [
                ("HID SEND", sendHID),
                ("ENTER", sendHIDEnter),
                ("BKSP", { ble.send(.backspace) }),
                ("CTRL-C", { ble.send(.ctrlC) }),
                ("BLE ON", { ble.connect() }),
                ("BLE OFF", { ble.disconnect() }),
                ("STOP", { ble.send(.stop) }),
                ("RESUME", { ble.send(.resume) })
            ]
        return LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 6), count: 4), spacing: 6) {
            ForEach(controls.indices, id: \.self) { index in
                Button(controls[index].0, action: controls[index].1)
                    .lineLimit(1)
                    .minimumScaleFactor(0.75)
                    .frame(maxWidth: .infinity, minHeight: 44)
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
            }
        }
    }

    private var codexComposer: some View {
        VStack(spacing: 6) {
            TextEditor(text: $codexPrompt)
                .frame(minHeight: 72, maxHeight: 120)
                .overlay(RoundedRectangle(cornerRadius: 6).stroke(.secondary.opacity(0.3)))
                .overlay(alignment: .topLeading) {
                    if codexPrompt.isEmpty {
                        Text("Codex prompt")
                            .foregroundStyle(.secondary)
                            .padding(.top, 8)
                            .padding(.leading, 5)
                            .allowsHitTesting(false)
                    }
                }
            HStack(spacing: 6) {
                Button("SEND TO CODEX") {
                    let value = codexPrompt
                    Task { if await session.sendCodexPrompt(value) { codexPrompt = "" } }
                }
                .disabled(codexPrompt.isEmpty)
                Button("STOP") { Task { _ = await session.cancelCodex() } }
                Button("NEW") { Task { _ = await session.newCodexSession() } }
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.small)
        }
    }

    private var settingsSheet: some View {
        NavigationStack {
            Form {
                Section("Terminal") {
                    TextField("WebSocket endpoint", text: $endpoint)
                        .focused($focusedField, equals: .endpoint)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    Text("TERM \(session.state.label)")
                        .font(.caption.monospaced())
                        .foregroundStyle(.secondary)
                    Text(session.statusMessage)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    Button("CONNECT") { session.connect(endpoint: endpoint) }
                        .disabled(!session.canConnect)
                    Button("DISCONNECT") { session.disconnect() }
                        .disabled(!session.canDisconnect)
                    Button("CLEAR") {
                        session.clearVisibleHistory()
                    }
                    Button("SEND") {
                        let value = command
                        Task { if await session.sendInput(value) { command = "" } }
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationDetents([.medium])
    }

    private var diagnosticsSheet: some View {
        NavigationStack {
            VStack(spacing: 8) {
                ScrollView {
                    Text(ble.eventLog.joined(separator: "\n"))
                        .font(.caption2.monospaced())
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                HStack {
                    Button("COPY LOG") {
                        UIPasteboard.general.string = ble.eventLog.joined(separator: "\n")
                    }
                    Button("CLEAR LOG") { ble.clearEventLog() }
                }
                .buttonStyle(.bordered)
            }
            .padding()
            .navigationTitle("Diagnostics")
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationDetents([.medium, .large])
    }

    private func sendHID() {
        let value = command
        ble.sendText(value) { success in if success { command = "" } }
    }

    private func sendHIDEnter() {
        ble.send(.enter)
    }
}

private extension BLEBridgeSession.State {
    var uiLabel: String {
        switch self {
        case .off: return "OFF"
        case .scanning: return "SCAN"
        case .connecting: return "CONNECTING"
        case .on: return "ON"
        case .stopped: return "STOPPED"
        case .error: return "ERROR"
        }
    }
}
