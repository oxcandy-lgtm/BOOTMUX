import SwiftUI
import UIKit

enum BOOTMUXClientMode: String {
    case directPTY = "DIRECT PTY"
    case hidMirror = "HID MIRROR"
    case codex = "CODEX"
}

enum BOOTMUXScenePhasePolicy {
    static func disconnects(for phase: ScenePhase) -> Bool {
        phase == .background
    }
}

enum BOOTMUXStatusText {
    static func ble(_ label: String) -> String {
        "BLE LINK: \(label)"
    }

    static func wifi(_ rawValue: String) -> String {
        "L11 UPLINK: \(rawValue)"
    }
}

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var session = TerminalSession()
    @StateObject private var ble = BLEBridgeSession()
    @AppStorage("bootmux.lastSuccessfulEndpoint") private var lastSuccessfulEndpoint = ""
    @State private var endpoint = ""
    @State private var command = ""
    @State private var codexPrompt = ""
    @State private var mode: BOOTMUXClientMode = .directPTY
    @State private var followOutput = true
    @State private var visibleFeedback = ""
    @State private var feedbackToken = 0
    @State private var showSettings = false
    @State private var showDiagnostics = false
    @State private var wifiSSID = ""
    @State private var wifiPassword = ""
    @FocusState private var focusedField: InputField?

    private enum InputField { case command, endpoint }

    var body: some View {
        GeometryReader { proxy in
            VStack(spacing: 8) {
                compactHeader
                Picker("Mode", selection: $mode) {
                    ForEach([BOOTMUXClientMode.directPTY, .hidMirror, .codex], id: \.self) { item in
                        Text(item.rawValue).tag(item)
                    }
                }
                .pickerStyle(.segmented)
                if mode == .hidMirror {
                    Text("SOURCE: HID MIRROR  \(session.isMirror ? "MIRROR LIVE" : "MIRROR OFF")")
                        .font(.caption2.monospaced())
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                SelectableTerminalView(text: session.terminalText, follow: followOutput, scrollToken: feedbackToken)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .layoutPriority(10)
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(.secondary.opacity(0.3)))
                terminalActions
                if !visibleFeedback.isEmpty {
                    Text(visibleFeedback)
                        .font(.caption2.bold())
                        .foregroundStyle(.tint)
                }
                Text(session.statusMessage)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .leading)
                if mode == .codex {
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
                clearWiFiForm()
            }
        }
        .onAppear {
            if endpoint.isEmpty { endpoint = lastSuccessfulEndpoint }
        }
        .onChange(of: session.state) { _, state in
            if case .connected = state { persistEndpointIfSafe() }
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

    private var terminalActions: some View {
        HStack(spacing: 6) {
            Button("COPY ALL") { copyAll() }
            Button("CLEAR") { clearTerminal() }
            Button(followOutput ? "FOLLOW ON" : "FOLLOW OFF") { followOutput.toggle() }
        }
        .buttonStyle(.bordered)
        .controlSize(.small)
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
                    Button("CONNECT") { session.connect(endpoint: connectionEndpoint) }
                        .disabled(!session.canConnect)
                    Button("DISCONNECT") { session.disconnect() }
                        .disabled(!session.canDisconnect)
                    Button("CLEAR") { clearTerminal() }
                    Button("SEND") {
                        let value = command
                        Task { if await session.sendInput(value) { command = "" } }
                    }
                }
                Section("Network Bridge") {
                    Text(BOOTMUXStatusText.ble(ble.state.uiLabel))
                        .font(.caption.monospaced())
                    Text(BOOTMUXStatusText.wifi(ble.wifiState.rawValue))
                        .font(.caption.monospaced())
                    Text("USB ETHERNET: R7A composite preserved")
                        .font(.caption.monospaced())
                        .foregroundStyle(.secondary)
                    TextField("Wi-Fi SSID", text: $wifiSSID)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    SecureField("Wi-Fi password", text: $wifiPassword)
                    Text(ble.wifiStatusMessage)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Button("CONNECT S3 TO WI-FI") {
                        let ssid = wifiSSID
                        let password = wifiPassword
                        ble.provisionWiFi(ssid: ssid, password: password) { success in
                            if success { wifiPassword = "" }
                        }
                    }
                    .disabled(!ble.isOpenForWiFi || wifiSSID.isEmpty)
                    Button("CHECK UPLINK") { ble.requestWiFiStatus() }
                        .disabled(!ble.isOpenForWiFi)
                    Button("DISCONNECT / CLEAR") {
                        ble.clearWiFi { _ in clearWiFiForm() }
                    }
                    .disabled(!ble.isOpenForWiFi)
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .onDisappear { clearWiFiForm() }
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

    private var connectionEndpoint: String {
        guard mode == .hidMirror else { return endpoint }
        return endpoint.replacingOccurrences(of: "/v1/terminal", with: "/v1/mirror")
    }

    private func persistEndpointIfSafe() {
        guard let url = URL(string: endpoint),
              ["ws", "wss"].contains(url.scheme?.lowercased() ?? ""),
              url.user == nil, url.password == nil else { return }
        lastSuccessfulEndpoint = endpoint
    }

    private func copyAll() {
        UIPasteboard.general.string = session.terminalText
        showFeedback("COPIED")
    }

    private func clearTerminal() {
        session.clearVisibleHistory()
        feedbackToken += 1
        showFeedback("CLEARED")
    }

    private func clearWiFiForm() {
        wifiSSID = ""
        wifiPassword = ""
        ble.clearLocalWiFiCredentials()
    }

    private func showFeedback(_ message: String) {
        visibleFeedback = message
        let token = feedbackToken
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            guard token == feedbackToken else { return }
            visibleFeedback = ""
        }
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

private extension BLEBridgeSession {
    var isOpenForWiFi: Bool {
        state == .on || state == .stopped
    }
}
