#include <Arduino.h>
#include <BLE2902.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <USB.h>
#include <USBHIDKeyboard.h>

#include <algorithm>
#include <array>
#include <cctype>
#include <cstdint>
#include <cstring>
#include <string>

namespace {
constexpr char kServiceUUID[] = "7c1b0001-4b4f-4d55-9a01-42584d583101";
constexpr char kRxUUID[] = "7c1b0002-4b4f-4d55-9a01-42584d583101";
constexpr char kTxUUID[] = "7c1b0003-4b4f-4d55-9a01-42584d583101";
constexpr size_t kMaxPayload = 512;
constexpr size_t kMaxParts = 32;
constexpr size_t kCompletedCache = 16;
constexpr size_t kFrameQueueCapacity = 2;

USBHIDKeyboard Keyboard;
BLECharacteristic *txCharacteristic = nullptr;
bool connected = false;
bool outputEnabled = true;
bool stoppedLatch = false;
String activeSession;
uint32_t reassemblySeq = 0;
uint8_t reassemblyTotal = 0;
uint32_t reassemblyStarted = 0;
std::array<String, kMaxParts> parts;
std::array<bool, kMaxParts> received{};
std::array<uint32_t, kCompletedCache> completed{};
size_t completedIndex = 0;
std::array<String, kFrameQueueCapacity> frameQueue;
size_t frameQueueHead = 0;
size_t frameQueueTail = 0;
size_t frameQueueCount = 0;
portMUX_TYPE frameQueueMux = portMUX_INITIALIZER_UNLOCKED;

String escapeField(const String &value) {
  String result;
  result.reserve(value.length());
  for (size_t i = 0; i < value.length(); ++i) {
    char c = value[i];
    if (c == '|' || c == '\\' || c == '\n' || c == '\r') result += '\\';
    result += c;
  }
  return result;
}

void notify(const String &message) {
  if (txCharacteristic != nullptr) {
    txCharacteristic->setValue(message.c_str());
    txCharacteristic->notify();
  }
}

void logEvent(const char *event) {
  Serial.println(event);
}

bool enqueueFrame(const String &frame) {
  bool accepted = false;
  portENTER_CRITICAL(&frameQueueMux);
  if (frameQueueCount < kFrameQueueCapacity) {
    frameQueue[frameQueueTail] = frame;
    frameQueueTail = (frameQueueTail + 1) % kFrameQueueCapacity;
    ++frameQueueCount;
    accepted = true;
  }
  portEXIT_CRITICAL(&frameQueueMux);
  return accepted;
}

bool dequeueFrame(String &frame) {
  bool available = false;
  portENTER_CRITICAL(&frameQueueMux);
  if (frameQueueCount > 0) {
    frame = frameQueue[frameQueueHead];
    frameQueue[frameQueueHead] = "";
    frameQueueHead = (frameQueueHead + 1) % kFrameQueueCapacity;
    --frameQueueCount;
    available = true;
  }
  portEXIT_CRITICAL(&frameQueueMux);
  return available;
}

void releaseAll() {
  Keyboard.releaseAll();
}

void clearReassembly() {
  reassemblySeq = 0;
  reassemblyTotal = 0;
  reassemblyStarted = 0;
  for (size_t i = 0; i < parts.size(); ++i) { parts[i] = ""; received[i] = false; }
}

bool seenCompleted(uint32_t sequence) {
  return std::find(completed.begin(), completed.end(), sequence) != completed.end();
}

void rememberCompleted(uint32_t sequence) {
  completed[completedIndex++ % completed.size()] = sequence;
}

void clearCompleted() { completed.fill(0); completedIndex = 0; }

bool parseUInt(const String &value, uint32_t &result) {
  if (value.isEmpty()) return false;
  uint64_t parsed = 0;
  for (size_t i = 0; i < value.length(); ++i) {
    if (!isDigit(value[i])) return false;
    parsed = parsed * 10 + static_cast<uint8_t>(value[i] - '0');
    if (parsed > UINT32_MAX) return false;
  }
  result = static_cast<uint32_t>(parsed);
  return true;
}

bool splitFrame(const String &frame, std::array<String, 7> &fields, size_t &count) {
  count = 0;
  String field;
  bool escaped = false;
  for (size_t i = 0; i < frame.length(); ++i) {
    char c = frame[i];
    if (escaped) {
      if (c == 'n') field += '\n';
      else if (c == 'r') field += '\r';
      else field += c;
      escaped = false;
      continue;
    }
    if (c == '\\') { escaped = true; continue; }
    if (c == '|') {
      if (count >= fields.size()) return false;
      fields[count++] = field;
      field = "";
    } else field += c;
  }
  if (escaped || count >= fields.size()) return false;
  fields[count++] = field;
  return true;
}

void typeASCII(const String &text) {
  if (!outputEnabled) return;
  for (size_t i = 0; i < text.length(); ++i) {
    uint8_t c = static_cast<uint8_t>(text[i]);
    if (c < 0x20 || c > 0x7e) continue;
    Keyboard.write(c);
    if ((i + 1) % 8 == 0) delay(1);
  }
  releaseAll();
  delay(1);
}

void applyControl(const String &session, uint32_t sequence, const String &control) {
  if (session != activeSession) return;
  Serial.printf("CTRL received: seq=%lu, kind=%s\n", static_cast<unsigned long>(sequence), control.c_str());
  if (seenCompleted(sequence)) {
    notify("BMX1|ACK|" + session + "|" + String(sequence) + "|DUPLICATE");
    return;
  }
  if (control == "STOP") {
    releaseAll();
    clearReassembly();
    stoppedLatch = true;
    outputEnabled = false;
    rememberCompleted(sequence);
    notify("BMX1|ACK|" + session + "|" + String(sequence) + "|STOPPED");
    return;
  }
  if (control == "RESUME") {
    outputEnabled = true;
    stoppedLatch = false;
    releaseAll();
    rememberCompleted(sequence);
    notify("BMX1|ACK|" + session + "|" + String(sequence) + "|RESUMED");
    return;
  }
  if (stoppedLatch || !outputEnabled) {
    releaseAll();
    notify("BMX1|ACK|" + session + "|" + String(sequence) + "|STOPPED");
    return;
  }
  if (control == "ENTER") Keyboard.write(KEY_RETURN);
  else if (control == "BACKSPACE") Keyboard.write(KEY_BACKSPACE);
  else if (control == "CTRL_C") { Keyboard.press(KEY_LEFT_CTRL); Keyboard.write('c'); releaseAll(); }
  releaseAll();
  rememberCompleted(sequence);
  notify("BMX1|ACK|" + session + "|" + String(sequence) + "|APPLIED");
}

void finishText(const String &session, uint32_t sequence) {
  Serial.printf("TEXT complete: seq=%lu\n", static_cast<unsigned long>(sequence));
  if (seenCompleted(sequence)) {
    notify("BMX1|ACK|" + session + "|" + String(sequence) + "|DUPLICATE");
    return;
  }
  if (stoppedLatch || !outputEnabled) {
    clearReassembly();
    releaseAll();
    notify("BMX1|ACK|" + session + "|" + String(sequence) + "|STOPPED");
    return;
  }
  String text;
  for (uint8_t i = 0; i < reassemblyTotal; ++i) text += parts[i];
  if (text.length() > kMaxPayload) { clearReassembly(); releaseAll(); notify("BMX1|ERR|" + session + "|" + String(sequence) + "|oversized_text"); return; }
  typeASCII(text);
  rememberCompleted(sequence);
  clearReassembly();
  notify("BMX1|ACK|" + session + "|" + String(sequence) + "|APPLIED");
}

void handleFrame(const String &frame) {
  std::array<String, 7> fields;
  size_t count = 0;
  if (!splitFrame(frame, fields, count) || count < 3 || fields[0] != "BMX1") { logEvent("FRAME rejected: malformed"); releaseAll(); return; }
  if (fields[1] == "OPEN" && count == 3) {
    logEvent("OPEN received");
    releaseAll(); clearReassembly(); clearCompleted(); activeSession = fields[2];
    outputEnabled = !stoppedLatch;
    notify("BMX1|ACK|" + activeSession + "|0|OPENED");
    return;
  }
  if (count < 5 || fields[2] != activeSession) { releaseAll(); return; }
  uint32_t sequence = 0;
  if (!parseUInt(fields[3], sequence)) { releaseAll(); return; }
  if (fields[1] == "CTRL") { applyControl(fields[2], sequence, fields[4]); return; }
  if (fields[1] != "TEXT" || count != 7) return;
  uint32_t part = 0, total = 0;
  if (!parseUInt(fields[4], part) || !parseUInt(fields[5], total) || total == 0 || total > kMaxParts || part >= total) return;
  if (reassemblySeq != 0 && (reassemblySeq != sequence || reassemblyTotal != total)) clearReassembly();
  if (reassemblySeq == 0) { reassemblySeq = sequence; reassemblyTotal = static_cast<uint8_t>(total); reassemblyStarted = millis(); }
  if (millis() - reassemblyStarted > 2000) { clearReassembly(); releaseAll(); notify("BMX1|ERR|" + activeSession + "|" + String(sequence) + "|reassembly_timeout"); return; }
  if (!received[part]) { parts[part] = fields[6]; received[part] = true; }
  bool complete = true;
  for (uint32_t i = 0; i < total; ++i) complete = complete && received[i];
  if (complete) finishText(activeSession, sequence);
}

class ServerCallbacks final : public BLEServerCallbacks {
  void onConnect(BLEServer *) override { connected = true; logEvent("BLE connected"); }
  void onDisconnect(BLEServer *) override { connected = false; logEvent("BLE disconnected"); releaseAll(); clearReassembly(); activeSession = ""; outputEnabled = false; BLEDevice::startAdvertising(); }
};

class RxCallbacks final : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *characteristic) override {
    String frame = characteristic->getValue().c_str();
    if (!enqueueFrame(frame)) {
      logEvent("FRAME rejected: queue overflow");
      releaseAll();
    }
  }
};
}

void setup() {
  Serial.begin(115200);
  logEvent("BOOTMUX firmware starting");
  // Set the native USB descriptors before TinyUSB is started.  The BLE name
  // below is independent from the USB product string seen by the host.
  USB.manufacturerName("BOOTMUX");
  USB.productName("BOOTMUX Keyboard");
  Keyboard.begin();
  USB.begin();
  BLEDevice::init("BOOTMUX Keyboard");
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());
  BLEService *service = server->createService(kServiceUUID);
  BLECharacteristic *rx = service->createCharacteristic(kRxUUID, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  txCharacteristic = service->createCharacteristic(kTxUUID, BLECharacteristic::PROPERTY_NOTIFY | BLECharacteristic::PROPERTY_READ);
  txCharacteristic->addDescriptor(new BLE2902());
  rx->setCallbacks(new RxCallbacks());
  service->start();
  BLEAdvertising *advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(kServiceUUID);
  advertising->setScanResponse(true);
  advertising->start();
  logEvent("BLE advertising started");
}

void loop() {
  String frame;
  if (dequeueFrame(frame)) handleFrame(frame);
  if (reassemblySeq != 0 && millis() - reassemblyStarted > 2000) { clearReassembly(); releaseAll(); }
  delay(10);
}
