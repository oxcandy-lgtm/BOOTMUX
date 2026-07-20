import CoreBluetooth
import Foundation

@MainActor
final class BLEBridgeSession: NSObject, ObservableObject {
    enum State: Equatable { case off, scanning, connecting, on, stopped, error(String) }

    @Published private(set) var state: State = .off
    @Published private(set) var statusMessage = "BLE off."

    private var central: CBCentralManager!
    private var peripheral: CBPeripheral?
    private var rx: CBCharacteristic?
    private var tx: CBCharacteristic?
    private var generation = 0
    private var sessionID = ""
    private var sequence: UInt32 = 0
    private var pendingWrites: [Data] = []
    private var writeInFlight = false
    private var pendingAck: ((Bool) -> Void)?

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
        generation += 1
        pendingWrites.removeAll()
        writeInFlight = false
        pendingAck = nil
        if let peripheral { central.cancelPeripheralConnection(peripheral) }
        peripheral = nil; rx = nil; tx = nil; sessionID = ""
        state = .off
        statusMessage = "BLE disconnected."
    }

    func sendText(_ text: String) {
        guard state == .on else { statusMessage = "Connect BLE before sending HID text."; return }
        sequence &+= 1
        do {
            let maximum = max(20, peripheral?.maximumWriteValueLength(for: .withResponse) ?? 20)
            let chunks = try BLEChunker(maximumWriteBytes: maximum).frames(session: sessionID, sequence: sequence, text: text)
            pendingWrites.append(contentsOf: chunks)
            pumpWrites()
        } catch { state = .error("HID text rejected.") }
    }

    func send(_ control: BLEControl) {
        guard state == .on || (state == .stopped && control == .resume) else { return }
        sequence &+= 1
        do { pendingWrites.append(try BLEProtocol.control(session: sessionID, sequence: sequence, control: control)); pumpWrites() }
        catch { state = .error("HID control rejected.") }
    }

    private func pumpWrites() {
        guard !writeInFlight, let rx, let peripheral, !pendingWrites.isEmpty else { return }
        writeInFlight = true
        let frame = pendingWrites.removeFirst()
        peripheral.writeValue(frame, for: rx, type: .withResponse)
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
            self.sessionID = UUID().uuidString.replacingOccurrences(of: "-", with: ""); self.generation += 1
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
            if let tx = self.tx { peripheral.setNotifyValue(true, for: tx) }
            guard let rx = self.rx else { self.state = .error("BOOTMUX BLE characteristic missing."); return }
            do { self.pendingWrites.append(try BLEProtocol.open(session: self.sessionID)); self.state = .on; self.statusMessage = "BLE connected."; self.pumpWrites(); _ = rx } catch { self.state = .error("BLE session open failed.") }
        }
    }

    nonisolated func peripheral(_ peripheral: CBPeripheral, didWriteValueFor characteristic: CBCharacteristic, error: Error?) {
        Task { @MainActor [weak self] in
            guard let self else { return }
            self.writeInFlight = false
            if error != nil { self.state = .error("BLE write failed."); self.pendingWrites.removeAll(); return }
            self.pumpWrites()
        }
    }

    nonisolated func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
        guard error == nil, let data = characteristic.value, let ack = BLEProtocol.parseAck(data) else { return }
        Task { @MainActor [weak self] in
            guard let self, ack.session == self.sessionID else { return }
            if ack.result == "STOPPED" { self.state = .stopped }
            if ack.result == "APPLIED" || ack.result == "DUPLICATE" { self.pendingAck?(true); self.pendingAck = nil }
        }
    }
}
