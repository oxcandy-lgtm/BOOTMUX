import CoreBluetooth
import Foundation

@MainActor
final class BLEBridgeSession: NSObject, ObservableObject {
    enum State: Equatable { case off, scanning, connecting, on, stopped, error(String) }

    private enum OperationKind { case text, control(BLEControl) }
    private struct PendingOperation {
        let session: String
        let sequence: UInt32
        let kind: OperationKind
        let frames: [Data]
        var nextFrame: Int
        let originalCommand: String?
        let completion: (Bool) -> Void
    }

    @Published private(set) var state: State = .off
    @Published private(set) var statusMessage = "BLE off."

    private var central: CBCentralManager!
    private var peripheral: CBPeripheral?
    private var rx: CBCharacteristic?
    private var tx: CBCharacteristic?
    private var sessionID = ""
    private var sequence: UInt32 = 0
    private var pendingOperation: PendingOperation?
    private var operationTimeoutTask: Task<Void, Never>?
    private var writeInFlight = false
    private var opening = false

    override init() {
        super.init()
        central = CBCentralManager(delegate: self, queue: nil)
    }

    func connect() {
        guard central.state == .poweredOn else { state = .error("Bluetooth is unavailable."); return }
        guard peripheral == nil else { statusMessage = "BLE already connected or connecting."; return }
        state = .scanning
        statusMessage = "Scanning for BOOTMUX Keyboard."
        central.scanForPeripherals(withServices: [CBUUID(string: BLEProtocol.serviceUUID)], options: [CBCentralManagerScanOptionAllowDuplicatesKey: false])
    }

    func disconnect() {
        central.stopScan()
        operationTimeoutTask?.cancel()
        operationTimeoutTask = nil
        pendingOperation?.completion(false)
        pendingOperation = nil
        writeInFlight = false
        opening = false
        if let peripheral { central.cancelPeripheralConnection(peripheral) }
        peripheral = nil; rx = nil; tx = nil; sessionID = ""
        state = .off
        statusMessage = "BLE disconnected."
    }

    func sendText(_ text: String, completion: @escaping (Bool) -> Void = { _ in }) {
        guard state == .on, pendingOperation == nil, let peripheral else {
            statusMessage = pendingOperation == nil ? "Connect BLE before sending HID text." : "Complete the current HID operation first."
            completion(false)
            return
        }
        sequence &+= 1
        do {
            let maximum = max(20, peripheral.maximumWriteValueLength(for: .withResponse))
            let frames = try BLEChunker(maximumWriteBytes: maximum).frames(session: sessionID, sequence: sequence, text: text)
            pendingOperation = PendingOperation(session: sessionID, sequence: sequence, kind: .text, frames: frames, nextFrame: 0, originalCommand: text, completion: completion)
            pumpOperation()
        } catch {
            statusMessage = "HID text rejected."
            completion(false)
        }
    }

    func send(_ control: BLEControl, completion: @escaping (Bool) -> Void = { _ in }) {
        let allowed = state == .on || (state == .stopped && control == .resume)
        guard allowed, pendingOperation == nil else {
            statusMessage = pendingOperation == nil ? "Connect BLE before sending HID control." : "Complete the current HID operation first."
            completion(false)
            return
        }
        sequence &+= 1
        do {
            let frame = try BLEProtocol.control(session: sessionID, sequence: sequence, control: control)
            pendingOperation = PendingOperation(session: sessionID, sequence: sequence, kind: .control(control), frames: [frame], nextFrame: 0, originalCommand: nil, completion: completion)
            pumpOperation()
        } catch {
            statusMessage = "HID control rejected."
            completion(false)
        }
    }

    private func pumpOperation() {
        guard !writeInFlight, var operation = pendingOperation, let peripheral, let rx else { return }
        guard operation.nextFrame < operation.frames.count else { armOperationTimeout(); return }
        writeInFlight = true
        let frame = operation.frames[operation.nextFrame]
        operation.nextFrame += 1
        pendingOperation = operation
        peripheral.writeValue(frame, for: rx, type: .withResponse)
    }

    private func armOperationTimeout() {
        operationTimeoutTask?.cancel()
        operationTimeoutTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            guard !Task.isCancelled else { return }
            self?.failPendingOperation("BLE ACK timeout.")
        }
    }

    private func finishPendingOperation(success: Bool, message: String) {
        operationTimeoutTask?.cancel()
        operationTimeoutTask = nil
        let completion = pendingOperation?.completion
        pendingOperation = nil
        statusMessage = message
        completion?(success)
    }

    private func failPendingOperation(_ message: String) {
        guard pendingOperation != nil else { return }
        finishPendingOperation(success: false, message: message)
    }

    private func handleAck(_ ack: (session: String, sequence: UInt32, result: String)) {
        guard ack.session == sessionID else { return }
        if opening, ack.sequence == 0, ack.result == "OPENED" {
            opening = false
            state = .on
            statusMessage = "BLE connected."
            return
        }
        guard var operation = pendingOperation, operation.session == ack.session, operation.sequence == ack.sequence else { return }
        switch ack.result {
        case "APPLIED", "DUPLICATE":
            if case .control(.stop) = operation.kind { state = .stopped }
            if case .control(.resume) = operation.kind { state = .on }
            finishPendingOperation(success: true, message: ack.result == "DUPLICATE" ? "HID operation already applied." : "HID operation applied.")
        case "STOPPED":
            if case .control(.stop) = operation.kind {
                state = .stopped
                finishPendingOperation(success: true, message: "HID stopped.")
            } else {
                state = .stopped
                finishPendingOperation(success: false, message: "HID output is stopped.")
            }
        default:
            _ = operation
        }
    }
}

extension BLEBridgeSession: CBCentralManagerDelegate {
    nonisolated func centralManagerDidUpdateState(_ central: CBCentralManager) {
        Task { @MainActor [weak self] in
            guard let self else { return }
            if central.state != .poweredOn { self.state = .off; self.statusMessage = "Bluetooth is unavailable." }
        }
    }

    nonisolated func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral, advertisementData: [String : Any], rssi RSSI: NSNumber) {
        Task { @MainActor [weak self] in
            guard let self, self.peripheral == nil else { return }
            central.stopScan(); self.peripheral = peripheral; peripheral.delegate = self; self.state = .connecting
            central.connect(peripheral)
        }
    }

    nonisolated func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        Task { @MainActor [weak self] in
            guard let self else { return }
            self.sessionID = UUID().uuidString.replacingOccurrences(of: "-", with: "")
            peripheral.discoverServices([CBUUID(string: BLEProtocol.serviceUUID)])
        }
    }

    nonisolated func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
        Task { @MainActor [weak self] in self?.disconnect() }
    }
}

extension BLEBridgeSession: CBPeripheralDelegate {
    nonisolated func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        guard let service = peripheral.services?.first(where: { $0.uuid == CBUUID(string: BLEProtocol.serviceUUID) }) else { return }
        peripheral.discoverCharacteristics([CBUUID(string: BLEProtocol.rxUUID), CBUUID(string: BLEProtocol.txUUID)], for: service)
    }

    nonisolated func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        Task { @MainActor [weak self] in
            guard let self, let characteristics = service.characteristics else { return }
            self.rx = characteristics.first(where: { $0.uuid == CBUUID(string: BLEProtocol.rxUUID) })
            self.tx = characteristics.first(where: { $0.uuid == CBUUID(string: BLEProtocol.txUUID) })
            guard let tx = self.tx, self.rx != nil else { self.state = .error("BOOTMUX BLE characteristic missing."); return }
            peripheral.setNotifyValue(true, for: tx)
        }
    }

    nonisolated func peripheral(_ peripheral: CBPeripheral, didUpdateNotificationStateFor characteristic: CBCharacteristic, error: Error?) {
        Task { @MainActor [weak self] in
            guard let self, characteristic.uuid == CBUUID(string: BLEProtocol.txUUID), error == nil, characteristic.isNotifying else { return }
            do {
                self.opening = true
                self.writeInFlight = true
                peripheral.writeValue(try BLEProtocol.open(session: self.sessionID), for: self.rx!, type: .withResponse)
            } catch { self.state = .error("BLE session open failed.") }
        }
    }

    nonisolated func peripheral(_ peripheral: CBPeripheral, didWriteValueFor characteristic: CBCharacteristic, error: Error?) {
        Task { @MainActor [weak self] in
            guard let self else { return }
            self.writeInFlight = false
            if error != nil { self.state = .error("BLE write failed."); self.failPendingOperation("BLE write failed."); return }
            self.pumpOperation()
        }
    }

    nonisolated func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
        guard error == nil, let data = characteristic.value, let ack = BLEProtocol.parseAck(data) else { return }
        Task { @MainActor [weak self] in self?.handleAck(ack) }
    }
}
