#include "ble_wifi_runtime.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "cJSON.h"
#include "driver/gpio.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "host/ble_hs.h"
#include "host/ble_hs_id.h"
#include "host/ble_gatt.h"
#include "host/util/util.h"
#include "mbedtls/base64.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "os/os_mbuf.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"
#include "esp_nimble_hci.h"
#include "class/hid/hid.h"
#include "tusb.h"

#define BMX_MAX_FRAME 520
#define BMX_FRAME_QUEUE 32
#define BMX_NOTIFY_QUEUE 16
#define BMX_WIFI_QUEUE 2
#define BMX_MAX_PAYLOAD 512
#define BMX_WIFI_DECODED_MAX 192
#define BMX_MAX_PARTS 32
#define BMX_WIFI_PARTS 16
#define BMX_FIELD_MAX 520
#define BMX_REASSEMBLY_TIMEOUT_MS 2000
#define BMX_WIFI_TIMEOUT_MS 15000
#define BMX_WIFI_TRIES 3
#define BMX_WIFI_EVENT_QUEUE 8
#define BMX_HID_REPORT_TIMEOUT_MS 250

static const char *kDeviceName = "BOOTMUX Bridge";
static const char *TAG = "bootmux_r7b";

typedef struct {
    uint16_t length;
    char bytes[BMX_MAX_FRAME];
} bmx_frame_t;

typedef struct {
    uint16_t length;
    char bytes[192];
} bmx_notification_t;

typedef struct {
    char session[64];
    uint32_t sequence;
    /* Base64 expands the bounded 192-byte JSON payload; keep queue storage bounded. */
    char payload[384];
    uint16_t length;
} wifi_command_t;

typedef struct {
    int32_t event_id;
    uint8_t reason;
} wifi_runtime_event_t;

typedef enum {
    WIFI_IDLE,
    WIFI_CONNECTING,
    WIFI_ONLINE,
    WIFI_AUTH_FAILED,
    WIFI_AP_NOT_FOUND,
    WIFI_NO_IP,
    WIFI_DISCONNECTED,
    WIFI_CLEARED,
} wifi_state_t;

static QueueHandle_t s_frames;
static QueueHandle_t s_notifications;
static QueueHandle_t s_wifi_commands;
static QueueHandle_t s_wifi_events;
static bool s_tasks_started;
static esp_netif_t *s_sta_netif;
static volatile bool s_queue_overflow;
static volatile bool s_connected;
static uint16_t s_conn_handle = BLE_HS_CONN_HANDLE_NONE;
static uint16_t s_tx_handle;
static uint8_t s_own_addr_type;
static char s_session[64];
static bool s_output_enabled;
static bool s_stopped;
static wifi_state_t s_wifi_state = WIFI_IDLE;
static int64_t s_wifi_deadline;
static uint8_t s_wifi_attempts;

static uint32_t s_completed[16];
static size_t s_completed_index;
static uint32_t s_text_sequence;
static uint8_t s_text_total;
static int64_t s_text_started;
static char s_text_parts[BMX_MAX_PARTS][BMX_FIELD_MAX];
static bool s_text_received[BMX_MAX_PARTS];

static uint32_t s_wifi_sequence;
static uint8_t s_wifi_total;
static int64_t s_wifi_started;
static char s_wifi_parts[BMX_WIFI_PARTS][BMX_FIELD_MAX];
static bool s_wifi_received[BMX_WIFI_PARTS];

static const ble_uuid128_t s_service_uuid = BLE_UUID128_INIT(
    0x01, 0x31, 0x58, 0x4d, 0x58, 0x42, 0x01, 0x9a,
    0x55, 0x4d, 0x4f, 0x4b, 0x01, 0x00, 0x1b, 0x7c);
static const ble_uuid128_t s_rx_uuid = BLE_UUID128_INIT(
    0x02, 0x31, 0x58, 0x4d, 0x58, 0x42, 0x01, 0x9a,
    0x55, 0x4d, 0x4f, 0x4b, 0x02, 0x00, 0x1b, 0x7c);
static const ble_uuid128_t s_tx_uuid = BLE_UUID128_INIT(
    0x03, 0x31, 0x58, 0x4d, 0x58, 0x42, 0x01, 0x9a,
    0x55, 0x4d, 0x4f, 0x4b, 0x03, 0x00, 0x1b, 0x7c);

static void secure_zero(void *memory, size_t length) {
    volatile uint8_t *bytes = (volatile uint8_t *)memory;
    while (length--) *bytes++ = 0;
}

static const char *wifi_state_name(wifi_state_t state) {
    switch (state) {
        case WIFI_IDLE: return "WIFI_IDLE";
        case WIFI_CONNECTING: return "WIFI_CONNECTING";
        case WIFI_ONLINE: return "WIFI_ONLINE";
        case WIFI_AUTH_FAILED: return "WIFI_AUTH_FAILED";
        case WIFI_AP_NOT_FOUND: return "WIFI_AP_NOT_FOUND";
        case WIFI_NO_IP: return "WIFI_NO_IP";
        case WIFI_DISCONNECTED: return "WIFI_DISCONNECTED";
        case WIFI_CLEARED: return "WIFI_CLEARED";
    }
    return "WIFI_IDLE";
}

static bool notify_enqueue(const char *message) {
    if (!s_notifications || !message) return false;
    size_t length = strnlen(message, sizeof(((bmx_notification_t *)0)->bytes));
    if (length == 0 || length >= sizeof(((bmx_notification_t *)0)->bytes)) return false;
    bmx_notification_t notification = {0};
    notification.length = (uint16_t)length;
    memcpy(notification.bytes, message, length);
    return xQueueSend(s_notifications, &notification, 0) == pdTRUE;
}

static void notify_ack(uint32_t sequence, const char *result) {
    char message[192];
    snprintf(message, sizeof(message), "BMX1|ACK|%s|%lu|%s", s_session,
             (unsigned long)sequence, result);
    (void)notify_enqueue(message);
}

static void notify_error(uint32_t sequence, const char *code) {
    char message[192];
    snprintf(message, sizeof(message), "BMX1|ERR|%s|%lu|%s", s_session,
             (unsigned long)sequence, code);
    (void)notify_enqueue(message);
}

static void notify_network(void) {
    char message[192];
    snprintf(message, sizeof(message), "BMX1|NET|%s|0|%s", s_session,
             wifi_state_name(s_wifi_state));
    (void)notify_enqueue(message);
}

static void set_wifi_state(wifi_state_t state) {
    s_wifi_state = state;
    notify_network();
}

static bool enqueue_frame(const uint8_t *data, size_t length) {
    if (!s_frames || !data || length == 0 || length >= BMX_MAX_FRAME) {
        s_queue_overflow = true;
        return false;
    }
    bmx_frame_t frame = {0};
    frame.length = (uint16_t)length;
    memcpy(frame.bytes, data, length);
    if (xQueueSend(s_frames, &frame, 0) != pdTRUE) {
        s_queue_overflow = true;
        return false;
    }
    return true;
}

static bool parse_uint(const char *value, uint32_t *result) {
    if (!value || !*value || !result) return false;
    uint64_t parsed = 0;
    for (const char *cursor = value; *cursor; ++cursor) {
        if (*cursor < '0' || *cursor > '9') return false;
        parsed = parsed * 10u + (uint32_t)(*cursor - '0');
        if (parsed > UINT32_MAX) return false;
    }
    *result = (uint32_t)parsed;
    return true;
}

static bool split_frame(const char *frame, size_t length, char fields[7][BMX_FIELD_MAX], size_t *count) {
    size_t field = 0;
    size_t position = 0;
    bool escaped = false;
    memset(fields, 0, sizeof(char) * 7 * BMX_FIELD_MAX);
    for (size_t i = 0; i < length; ++i) {
        char value = frame[i];
        if (escaped) {
            if (position + 1 >= BMX_FIELD_MAX) return false;
            fields[field][position++] = value == 'n' ? '\n' : value == 'r' ? '\r' : value;
            escaped = false;
        } else if (value == '\\') {
            escaped = true;
        } else if (value == '|') {
            if (++field >= 7) return false;
            position = 0;
        } else {
            if (position + 1 >= BMX_FIELD_MAX) return false;
            fields[field][position++] = value;
        }
    }
    if (escaped) return false;
    *count = field + 1;
    return true;
}

static void clear_text_reassembly(void) {
    secure_zero(s_text_parts, sizeof(s_text_parts));
    memset(s_text_received, 0, sizeof(s_text_received));
    s_text_sequence = 0;
    s_text_total = 0;
    s_text_started = 0;
}

static void clear_wifi_reassembly(void) {
    secure_zero(s_wifi_parts, sizeof(s_wifi_parts));
    memset(s_wifi_received, 0, sizeof(s_wifi_received));
    s_wifi_sequence = 0;
    s_wifi_total = 0;
    s_wifi_started = 0;
}

static bool completed_sequence(uint32_t sequence) {
    for (size_t i = 0; i < sizeof(s_completed) / sizeof(s_completed[0]); ++i)
        if (s_completed[i] == sequence) return true;
    return false;
}

static void remember_sequence(uint32_t sequence) {
    s_completed[s_completed_index++ % (sizeof(s_completed) / sizeof(s_completed[0]))] = sequence;
}

static bool send_hid_report(const uint8_t report[8]) {
    const int64_t deadline = (esp_timer_get_time() / 1000) + BMX_HID_REPORT_TIMEOUT_MS;
    while ((esp_timer_get_time() / 1000) < deadline) {
        if (tud_hid_ready() && tud_hid_report(0, report, 8)) return true;
        vTaskDelay(pdMS_TO_TICKS(1));
    }
    return false;
}

static bool release_all(void) {
    uint8_t report[8] = {0};
    return send_hid_report(report);
}

static bool hid_key_for_ascii(char value, uint8_t *key, uint8_t *modifier) {
    *key = 0; *modifier = 0;
    if (value >= 'a' && value <= 'z') { *key = (uint8_t)(HID_KEY_A + value - 'a'); return true; }
    if (value >= 'A' && value <= 'Z') { *key = (uint8_t)(HID_KEY_A + value - 'A'); *modifier = 0x02; return true; }
    if (value >= '1' && value <= '9') { *key = (uint8_t)(HID_KEY_1 + value - '1'); return true; }
    switch (value) {
        case '0': *key = HID_KEY_0; return true;
        case ' ': *key = HID_KEY_SPACE; return true;
        case '!': *key = HID_KEY_1; *modifier = 0x02; return true;
        case '"': *key = HID_KEY_APOSTROPHE; *modifier = 0x02; return true;
        case '#': *key = HID_KEY_3; *modifier = 0x02; return true;
        case '$': *key = HID_KEY_4; *modifier = 0x02; return true;
        case '%': *key = HID_KEY_5; *modifier = 0x02; return true;
        case '&': *key = HID_KEY_7; *modifier = 0x02; return true;
        case '\'': *key = HID_KEY_APOSTROPHE; return true;
        case '(': *key = HID_KEY_9; *modifier = 0x02; return true;
        case ')': *key = HID_KEY_0; *modifier = 0x02; return true;
        case '*': *key = HID_KEY_8; *modifier = 0x02; return true;
        case '+': *key = HID_KEY_EQUAL; *modifier = 0x02; return true;
        case ',': *key = HID_KEY_COMMA; return true;
        case '-': *key = HID_KEY_MINUS; return true;
        case '.': *key = HID_KEY_PERIOD; return true;
        case '/': *key = HID_KEY_SLASH; return true;
        case ':': *key = HID_KEY_SEMICOLON; *modifier = 0x02; return true;
        case ';': *key = HID_KEY_SEMICOLON; return true;
        case '<': *key = HID_KEY_COMMA; *modifier = 0x02; return true;
        case '=': *key = HID_KEY_EQUAL; return true;
        case '>': *key = HID_KEY_PERIOD; *modifier = 0x02; return true;
        case '?': *key = HID_KEY_SLASH; *modifier = 0x02; return true;
        case '@': *key = HID_KEY_2; *modifier = 0x02; return true;
        case '[': *key = HID_KEY_BRACKET_LEFT; return true;
        case '\\': *key = HID_KEY_BACKSLASH; return true;
        case ']': *key = HID_KEY_BRACKET_RIGHT; return true;
        case '^': *key = HID_KEY_6; *modifier = 0x02; return true;
        case '_': *key = HID_KEY_MINUS; *modifier = 0x02; return true;
        case '`': *key = HID_KEY_GRAVE; return true;
        case '{': *key = HID_KEY_BRACKET_LEFT; *modifier = 0x02; return true;
        case '|': *key = HID_KEY_BACKSLASH; *modifier = 0x02; return true;
        case '}': *key = HID_KEY_BRACKET_RIGHT; *modifier = 0x02; return true;
        case '~': *key = HID_KEY_GRAVE; *modifier = 0x02; return true;
        default: return false;
    }
}

static bool validate_ascii_text(const char *text, size_t length) {
    for (size_t i = 0; i < length; ++i) {
        uint8_t key, modifier;
        if ((uint8_t)text[i] < 0x20 || (uint8_t)text[i] > 0x7e || !hid_key_for_ascii(text[i], &key, &modifier)) return false;
    }
    return true;
}

static bool type_ascii(const char *text, size_t length) {
    if (!s_output_enabled || !tud_hid_ready() || !validate_ascii_text(text, length)) return false;
    for (size_t i = 0; i < length; ++i) {
        uint8_t key, modifier;
        (void)hid_key_for_ascii(text[i], &key, &modifier);
        uint8_t report[8] = {0};
        report[0] = modifier;
        report[2] = key;
        if (!send_hid_report(report) || !release_all()) return false;
    }
    return true;
}

static void apply_control(const char *session, uint32_t sequence, const char *control) {
    if (strcmp(session, s_session) != 0) return;
    if (completed_sequence(sequence)) { notify_ack(sequence, "DUPLICATE"); return; }
    if (strcmp(control, "STOP") == 0) {
        release_all(); clear_text_reassembly(); s_stopped = true; s_output_enabled = false;
        remember_sequence(sequence); notify_ack(sequence, "STOPPED"); return;
    }
    if (strcmp(control, "RESUME") == 0) {
        release_all(); s_stopped = false; s_output_enabled = true;
        remember_sequence(sequence); notify_ack(sequence, "RESUMED"); return;
    }
    if (s_stopped || !s_output_enabled) { release_all(); notify_ack(sequence, "STOPPED"); return; }
    uint8_t report[8] = {0};
    if (strcmp(control, "ENTER") == 0) report[2] = HID_KEY_ENTER;
    else if (strcmp(control, "BACKSPACE") == 0) report[2] = HID_KEY_BACKSPACE;
    else if (strcmp(control, "CTRL_C") == 0) { report[0] = 0x01; report[2] = HID_KEY_C; }
    else { notify_error(sequence, "unknown_control"); return; }
    if (!send_hid_report(report) || !release_all()) {
        release_all();
        notify_error(sequence, "hid_not_ready");
        return;
    }
    remember_sequence(sequence); notify_ack(sequence, "APPLIED");
}

static void finish_text(uint32_t sequence) {
    if (completed_sequence(sequence)) { notify_ack(sequence, "DUPLICATE"); return; }
    if (s_stopped || !s_output_enabled) { clear_text_reassembly(); release_all(); notify_ack(sequence, "STOPPED"); return; }
    char text[BMX_MAX_PAYLOAD + 1] = {0};
    size_t used = 0;
    for (size_t i = 0; i < s_text_total; ++i) {
        size_t part_length = strlen(s_text_parts[i]);
        if (used + part_length > BMX_MAX_PAYLOAD) { clear_text_reassembly(); release_all(); notify_error(sequence, "oversized_text"); return; }
        memcpy(text + used, s_text_parts[i], part_length); used += part_length;
    }
    if (!type_ascii(text, used)) { secure_zero(text, sizeof(text)); clear_text_reassembly(); release_all(); notify_error(sequence, "hid_not_ready_or_unsupported"); return; }
    secure_zero(text, sizeof(text)); clear_text_reassembly(); remember_sequence(sequence); notify_ack(sequence, "APPLIED");
}

static bool decode_wifi_json(const char *encoded, size_t length, char *ssid, size_t ssid_size, char *password, size_t password_size) {
    uint8_t decoded[BMX_WIFI_DECODED_MAX + 1] = {0};
    size_t decoded_length = 0;
    if (mbedtls_base64_decode(decoded, sizeof(decoded) - 1, &decoded_length, (const unsigned char *)encoded, length) != 0 || decoded_length == 0 || decoded_length > BMX_WIFI_DECODED_MAX) {
        secure_zero(decoded, sizeof(decoded)); return false;
    }
    cJSON *root = cJSON_ParseWithLength((const char *)decoded, decoded_length);
    const cJSON *ssid_item = root ? cJSON_GetObjectItemCaseSensitive(root, "ssid") : NULL;
    const cJSON *password_item = root ? cJSON_GetObjectItemCaseSensitive(root, "password") : NULL;
    bool valid = cJSON_IsString(ssid_item) && cJSON_IsString(password_item) && ssid_item->valuestring && password_item->valuestring;
    if (valid) {
        size_t ssid_length = strnlen(ssid_item->valuestring, ssid_size + 1);
        size_t password_length = strnlen(password_item->valuestring, password_size + 1);
        valid = ssid_length > 0 && ssid_length <= 32 && password_length <= 63 && (password_length == 0 || password_length >= 8) && !memchr(ssid_item->valuestring, 0, ssid_length) && !memchr(password_item->valuestring, 0, password_length);
        if (valid) { memcpy(ssid, ssid_item->valuestring, ssid_length); ssid[ssid_length] = 0; memcpy(password, password_item->valuestring, password_length); password[password_length] = 0; }
    }
    if (ssid_item && ssid_item->valuestring) secure_zero(ssid_item->valuestring, strlen(ssid_item->valuestring));
    if (password_item && password_item->valuestring) secure_zero(password_item->valuestring, strlen(password_item->valuestring));
    if (root) cJSON_Delete(root);
    secure_zero(decoded, sizeof(decoded));
    return valid;
}

static void handle_wifi_command(const wifi_command_t *command);

static void wifi_event_handler(void *arg, esp_event_base_t base, int32_t id, void *data) {
    (void)arg;
    if (!s_wifi_events) return;
    wifi_runtime_event_t event = { .event_id = id, .reason = 0 };
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED && data) {
        const wifi_event_sta_disconnected_t *disconnected = data;
        event.reason = disconnected->reason;
    }
    (void)xQueueSend(s_wifi_events, &event, 0);
}

static void wifi_task(void *arg) {
    (void)arg;
    for (;;) {
        wifi_runtime_event_t event;
        if (xQueueReceive(s_wifi_events, &event, pdMS_TO_TICKS(250)) == pdTRUE) {
            if (event.event_id == WIFI_EVENT_STA_START) {
                set_wifi_state(WIFI_CONNECTING);
            } else if (event.event_id == WIFI_EVENT_STA_DISCONNECTED) {
                if (event.reason == WIFI_REASON_AUTH_FAIL || event.reason == WIFI_REASON_AUTH_EXPIRE || event.reason == WIFI_REASON_HANDSHAKE_TIMEOUT) {
                    s_wifi_deadline = 0;
                    set_wifi_state(WIFI_AUTH_FAILED);
                } else if (event.reason == WIFI_REASON_NO_AP_FOUND || event.reason == WIFI_REASON_NO_AP_FOUND_W_COMPATIBLE_SECURITY) {
                    s_wifi_deadline = 0;
                    set_wifi_state(WIFI_AP_NOT_FOUND);
                } else if (s_wifi_state != WIFI_AUTH_FAILED && s_wifi_state != WIFI_AP_NOT_FOUND && s_wifi_state != WIFI_NO_IP) {
                    set_wifi_state(WIFI_DISCONNECTED);
                }
            } else if (event.event_id == IP_EVENT_STA_GOT_IP) {
                s_wifi_deadline = 0;
                s_wifi_attempts = 0;
                set_wifi_state(WIFI_ONLINE);
            }
        }
        wifi_command_t command;
        if (xQueueReceive(s_wifi_commands, &command, 0) == pdTRUE) {
            handle_wifi_command(&command);
            secure_zero(&command, sizeof(command));
        }
        if (s_wifi_state == WIFI_CONNECTING && s_wifi_deadline > 0 && (esp_timer_get_time() / 1000) >= s_wifi_deadline) {
            if (s_wifi_attempts < BMX_WIFI_TRIES) {
                ++s_wifi_attempts;
                s_wifi_deadline = (esp_timer_get_time() / 1000) + BMX_WIFI_TIMEOUT_MS;
                esp_err_t disconnect_error = esp_wifi_disconnect();
                if (disconnect_error != ESP_OK && disconnect_error != ESP_ERR_WIFI_NOT_CONNECT) {
                    s_wifi_deadline = 0;
                    set_wifi_state(WIFI_NO_IP);
                    notify_error(0, "wifi_disconnect_failed");
                    continue;
                }
                esp_err_t connect_error = esp_wifi_connect();
                if (connect_error != ESP_OK) {
                    s_wifi_deadline = 0;
                    set_wifi_state(WIFI_NO_IP);
                    notify_error(0, "wifi_connect_start_failed");
                }
            } else {
                s_wifi_deadline = 0;
                esp_err_t disconnect_error = esp_wifi_disconnect();
                if (disconnect_error != ESP_OK && disconnect_error != ESP_ERR_WIFI_NOT_CONNECT) {
                    notify_error(0, "wifi_disconnect_failed");
                }
                set_wifi_state(WIFI_NO_IP);
            }
        }
    }
}

static void handle_wifi_command(const wifi_command_t *command) {
    char ssid[33] = {0}; char password[64] = {0};
    if (!decode_wifi_json(command->payload, command->length, ssid, sizeof(ssid), password, sizeof(password))) {
        notify_error(command->sequence, "invalid_wifi_payload"); secure_zero(ssid, sizeof(ssid)); secure_zero(password, sizeof(password)); return;
    }
    wifi_config_t config = {0};
    memcpy(config.sta.ssid, ssid, strlen(ssid)); memcpy(config.sta.password, password, strlen(password));
    secure_zero(ssid, sizeof(ssid)); secure_zero(password, sizeof(password));
    esp_err_t error = esp_wifi_set_storage(WIFI_STORAGE_RAM);
    if (error != ESP_OK) { secure_zero(&config, sizeof(config)); notify_error(command->sequence, "wifi_storage_failed"); return; }
    error = esp_wifi_set_mode(WIFI_MODE_STA);
    if (error != ESP_OK) { secure_zero(&config, sizeof(config)); notify_error(command->sequence, "wifi_mode_failed"); return; }
    error = esp_wifi_set_config(WIFI_IF_STA, &config);
    secure_zero(&config, sizeof(config));
    if (error != ESP_OK) { notify_error(command->sequence, "wifi_config_failed"); return; }
    set_wifi_state(WIFI_CONNECTING);
    s_wifi_attempts = 1;
    s_wifi_deadline = (esp_timer_get_time() / 1000) + BMX_WIFI_TIMEOUT_MS;
    error = esp_wifi_connect();
    if (error != ESP_OK) { s_wifi_deadline = 0; notify_error(command->sequence, "wifi_connect_start_failed"); return; }
    notify_ack(command->sequence, "APPLIED");
}

static void complete_wifi(uint32_t sequence) {
    /* 192 decoded bytes require at most 256 base64 bytes, plus framing slack. */
    char encoded[384] = {0};
    size_t used = 0;
    for (size_t i = 0; i < s_wifi_total; ++i) {
        size_t part_length = strlen(s_wifi_parts[i]);
        if (used + part_length >= sizeof(encoded)) { clear_wifi_reassembly(); notify_error(sequence, "oversized_wifi_payload"); return; }
        memcpy(encoded + used, s_wifi_parts[i], part_length); used += part_length;
    }
    wifi_command_t command = {0};
    strncpy(command.session, s_session, sizeof(command.session) - 1);
    command.sequence = sequence; command.length = (uint16_t)used; memcpy(command.payload, encoded, used);
    secure_zero(encoded, sizeof(encoded)); clear_wifi_reassembly();
    if (xQueueSend(s_wifi_commands, &command, 0) != pdTRUE) { secure_zero(&command, sizeof(command)); notify_error(sequence, "wifi_queue_overflow"); return; }
}

static void handle_frame(const bmx_frame_t *frame) {
    char fields[7][BMX_FIELD_MAX]; size_t count = 0;
    if (!split_frame(frame->bytes, frame->length, fields, &count) || count < 3 || strcmp(fields[0], "BMX1") != 0) return;
    if (strcmp(fields[1], "OPEN") == 0 && count == 3) {
        strncpy(s_session, fields[2], sizeof(s_session) - 1); s_session[sizeof(s_session) - 1] = 0;
        s_output_enabled = true; s_stopped = false; clear_text_reassembly(); clear_wifi_reassembly(); memset(s_completed, 0, sizeof(s_completed)); s_completed_index = 0;
        notify_ack(0, "OPENED"); notify_network(); return;
    }
    if (count < 5 || strcmp(fields[2], s_session) != 0) return;
    uint32_t sequence = 0;
    if (!parse_uint(fields[3], &sequence)) return;
    if (strcmp(fields[1], "CTRL") == 0 && count == 5) { apply_control(fields[2], sequence, fields[4]); return; }
    if (strcmp(fields[1], "TEXT") == 0 && count == 7) {
        uint32_t part = 0, total = 0;
        if (!parse_uint(fields[4], &part) || !parse_uint(fields[5], &total) || total == 0 || total > BMX_MAX_PARTS || part >= total) return;
        if (s_text_sequence && (s_text_sequence != sequence || s_text_total != total)) clear_text_reassembly();
        if (!s_text_sequence) { s_text_sequence = sequence; s_text_total = (uint8_t)total; s_text_started = esp_timer_get_time() / 1000; }
        if ((esp_timer_get_time() / 1000) - s_text_started > BMX_REASSEMBLY_TIMEOUT_MS) { clear_text_reassembly(); release_all(); notify_error(sequence, "reassembly_timeout"); return; }
        if (!s_text_received[part]) { strncpy(s_text_parts[part], fields[6], BMX_FIELD_MAX - 1); s_text_received[part] = true; }
        bool complete = true; for (size_t i = 0; i < total; ++i) complete = complete && s_text_received[i];
        if (complete) {
            finish_text(sequence);
        }
        return;
    }
    if (strcmp(fields[1], "WIFI") == 0 && count == 7) {
        uint32_t part = 0, total = 0;
        if (!parse_uint(fields[4], &part) || !parse_uint(fields[5], &total) || total == 0 || total > BMX_WIFI_PARTS || part >= total) return;
        if (s_wifi_sequence && (s_wifi_sequence != sequence || s_wifi_total != total)) clear_wifi_reassembly();
        if (!s_wifi_sequence) { s_wifi_sequence = sequence; s_wifi_total = (uint8_t)total; s_wifi_started = esp_timer_get_time() / 1000; }
        if ((esp_timer_get_time() / 1000) - s_wifi_started > BMX_REASSEMBLY_TIMEOUT_MS) { clear_wifi_reassembly(); notify_error(sequence, "wifi_reassembly_timeout"); return; }
        if (!s_wifi_received[part]) { strncpy(s_wifi_parts[part], fields[6], BMX_FIELD_MAX - 1); s_wifi_received[part] = true; }
        bool complete = true; for (size_t i = 0; i < total; ++i) complete = complete && s_wifi_received[i];
        if (complete) {
            complete_wifi(sequence);
        }
        return;
    }
    if (strcmp(fields[1], "WIFI_STATUS") == 0 && count == 5) { notify_network(); notify_ack(sequence, "APPLIED"); return; }
    if (strcmp(fields[1], "WIFI_CLEAR") == 0 && count == 5) {
        wifi_config_t empty = {0};
        esp_err_t error = esp_wifi_disconnect();
        if (error != ESP_OK && error != ESP_ERR_WIFI_NOT_CONNECT) { secure_zero(&empty, sizeof(empty)); notify_error(sequence, "wifi_disconnect_failed"); return; }
        error = esp_wifi_set_config(WIFI_IF_STA, &empty);
        secure_zero(&empty, sizeof(empty));
        if (error != ESP_OK) { notify_error(sequence, "wifi_clear_failed"); return; }
        s_wifi_deadline = 0;
        set_wifi_state(WIFI_CLEARED);
        notify_ack(sequence, "APPLIED");
        return;
    }
}

static int rx_write_cb(uint16_t conn_handle, uint16_t attr_handle, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    (void)conn_handle; (void)attr_handle; (void)arg;
    size_t length = OS_MBUF_PKTLEN(ctxt->om);
    uint8_t data[BMX_MAX_FRAME];
    if (length == 0 || length >= sizeof(data) || ble_hs_mbuf_to_flat(ctxt->om, data, sizeof(data), NULL) != 0 || !enqueue_frame(data, length)) { secure_zero(data, sizeof(data)); return BLE_ATT_ERR_INSUFFICIENT_RES; }
    secure_zero(data, sizeof(data)); return 0;
}

static int tx_notify_cb(uint16_t conn_handle, uint16_t attr_handle, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    (void)conn_handle; (void)attr_handle; (void)ctxt; (void)arg;
    return BLE_ATT_ERR_READ_NOT_PERMITTED;
}

static const struct ble_gatt_svc_def s_services[] = {
    { .type = BLE_GATT_SVC_TYPE_PRIMARY, .uuid = &s_service_uuid.u, .characteristics = (struct ble_gatt_chr_def[]) {
        { .uuid = &s_rx_uuid.u, .access_cb = rx_write_cb, .flags = BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_WRITE_NO_RSP },
        { .uuid = &s_tx_uuid.u, .access_cb = tx_notify_cb, .val_handle = &s_tx_handle, .flags = BLE_GATT_CHR_F_NOTIFY },
        { 0 }
    } },
    { 0 }
};

static int ble_advertise(void);

static void restart_advertising(void) {
    int rc = ble_advertise();
    if (rc != 0) ESP_LOGE(TAG, "BLE re-advertise failed rc=%d", rc);
}

static int gap_event(struct ble_gap_event *event, void *arg) {
    (void)arg;
    if (event->type == BLE_GAP_EVENT_CONNECT) {
        if (event->connect.status == 0) { s_connected = true; s_conn_handle = event->connect.conn_handle; }
        else restart_advertising();
    } else if (event->type == BLE_GAP_EVENT_DISCONNECT) {
        s_connected = false; s_conn_handle = BLE_HS_CONN_HANDLE_NONE; s_session[0] = 0; s_output_enabled = false; s_stopped = false; clear_text_reassembly(); clear_wifi_reassembly(); release_all();
        restart_advertising();
    } else if (event->type == BLE_GAP_EVENT_ADV_COMPLETE) {
        restart_advertising();
    }
    return 0;
}

static int ble_advertise(void) {
    struct ble_hs_adv_fields fields = {0};
    fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    fields.uuids128 = (ble_uuid128_t *)&s_service_uuid;
    fields.num_uuids128 = 1;
    fields.uuids128_is_complete = 1;
    int rc = ble_gap_adv_set_fields(&fields);
    if (rc != 0) return rc;

    struct ble_hs_adv_fields scan_response = {0};
    scan_response.name = (uint8_t *)kDeviceName;
    scan_response.name_len = strlen(kDeviceName);
    scan_response.name_is_complete = 1;
    rc = ble_gap_adv_rsp_set_fields(&scan_response);
    if (rc != 0) return rc;

    struct ble_gap_adv_params params = {0};
    params.conn_mode = BLE_GAP_CONN_MODE_UND;
    params.disc_mode = BLE_GAP_DISC_MODE_GEN;
    return ble_gap_adv_start(s_own_addr_type, NULL, BLE_HS_FOREVER, &params, gap_event, NULL);
}

static void ble_on_sync(void) {
    int rc = ble_hs_util_ensure_addr(0);
    if (rc != 0) { ESP_LOGE(TAG, "ensure BLE addr failed rc=%d", rc); return; }
    rc = ble_hs_id_infer_auto(0, &s_own_addr_type);
    if (rc != 0) { ESP_LOGE(TAG, "infer BLE addr failed rc=%d", rc); return; }
    rc = ble_advertise();
    if (rc != 0) { ESP_LOGE(TAG, "BLE advertise failed rc=%d", rc); return; }
    puts("BOOT_STAGE_ADV_OK");
}

static void ble_host_task(void *param) { (void)param; nimble_port_run(); nimble_port_freertos_deinit(); }

static void notify_task(void *arg) {
    (void)arg; bmx_notification_t notification;
    for (;;) {
        if (xQueueReceive(s_notifications, &notification, portMAX_DELAY) != pdTRUE) continue;
        if (!s_connected || s_conn_handle == BLE_HS_CONN_HANDLE_NONE) continue;
        struct os_mbuf *om = ble_hs_mbuf_from_flat(notification.bytes, notification.length);
        if (om) ble_gatts_notify_custom(s_conn_handle, s_tx_handle, om);
        secure_zero(&notification, sizeof(notification));
    }
}

static void dispatcher_task(void *arg) {
    (void)arg; bmx_frame_t frame;
    for (;;) {
        if (s_queue_overflow) { s_queue_overflow = false; notify_error(0, "queue_full"); }
        if (xQueueReceive(s_frames, &frame, pdMS_TO_TICKS(25)) == pdTRUE) { handle_frame(&frame); secure_zero(&frame, sizeof(frame)); }
        int64_t now = esp_timer_get_time() / 1000;
        if (s_text_sequence && now - s_text_started > BMX_REASSEMBLY_TIMEOUT_MS) clear_text_reassembly();
        if (s_wifi_sequence && now - s_wifi_started > BMX_REASSEMBLY_TIMEOUT_MS) clear_wifi_reassembly();
    }
}

static esp_err_t runtime_failure(const char *stage, esp_err_t error) {
    /* Queues are reclaimed only before any consumer task can run.  Once task
       creation begins, retaining them is safer than deleting live queues; the
       app remains in its USB-only loop and reports the failed stage. */
    if (!s_tasks_started) {
        if (s_frames) { vQueueDelete(s_frames); s_frames = NULL; }
        if (s_notifications) { vQueueDelete(s_notifications); s_notifications = NULL; }
        if (s_wifi_commands) { vQueueDelete(s_wifi_commands); s_wifi_commands = NULL; }
        if (s_wifi_events) { vQueueDelete(s_wifi_events); s_wifi_events = NULL; }
    }
    ESP_LOGE(TAG, "runtime init failed stage=%s code=%s", stage, esp_err_to_name(error));
    printf("BOOTMUX_RUNTIME_FAILED stage=%s code=%s\n", stage, esp_err_to_name(error));
    return error;
}

esp_err_t bootmux_ble_wifi_init(void) {
    s_frames = xQueueCreate(BMX_FRAME_QUEUE, sizeof(bmx_frame_t));
    s_notifications = xQueueCreate(BMX_NOTIFY_QUEUE, sizeof(bmx_notification_t));
    s_wifi_commands = xQueueCreate(BMX_WIFI_QUEUE, sizeof(wifi_command_t));
    s_wifi_events = xQueueCreate(BMX_WIFI_EVENT_QUEUE, sizeof(wifi_runtime_event_t));
    if (!s_frames || !s_notifications || !s_wifi_commands || !s_wifi_events) return runtime_failure("QUEUE", ESP_ERR_NO_MEM);
    puts("BOOT_STAGE_QUEUE_OK");

    esp_err_t error = esp_netif_init();
    if (error != ESP_OK) return runtime_failure("NETIF_INIT", error);
    error = esp_event_loop_create_default();
    if (error != ESP_OK) return runtime_failure("EVENT_LOOP", error);
    error = esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_event_handler, NULL);
    if (error != ESP_OK) return runtime_failure("WIFI_EVENT_HANDLER", error);
    error = esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, wifi_event_handler, NULL);
    if (error != ESP_OK) return runtime_failure("IP_EVENT_HANDLER", error);
    s_sta_netif = esp_netif_create_default_wifi_sta();
    if (!s_sta_netif) return runtime_failure("NETIF_CREATE", ESP_FAIL);
    puts("BOOT_STAGE_NETIF_OK");

    wifi_init_config_t wifi_config = WIFI_INIT_CONFIG_DEFAULT();
    wifi_config.nvs_enable = 0;
    puts("BOOT_STAGE_WIFI_NVS_DISABLED");
    error = esp_wifi_init(&wifi_config);
    if (error != ESP_OK) return runtime_failure("WIFI_INIT", error);
    error = esp_wifi_set_storage(WIFI_STORAGE_RAM);
    if (error != ESP_OK) return runtime_failure("WIFI_STORAGE", error);
    error = esp_wifi_set_mode(WIFI_MODE_STA);
    if (error != ESP_OK) return runtime_failure("WIFI_MODE", error);
    error = esp_wifi_start();
    if (error != ESP_OK) return runtime_failure("WIFI_START", error);
    puts("BOOT_STAGE_WIFI_OK");

    error = nimble_port_init();
    if (error != ESP_OK) return runtime_failure("NIMBLE", error);
    puts("BOOT_STAGE_NIMBLE_OK");
    ble_svc_gap_init();
    ble_svc_gatt_init();
    int ble_error = ble_svc_gap_device_name_set(kDeviceName);
    if (ble_error != 0) return runtime_failure("GAP_NAME", ESP_FAIL);
    ble_error = ble_gatts_count_cfg(s_services);
    if (ble_error != 0) return runtime_failure("GATT_COUNT", ESP_FAIL);
    ble_error = ble_gatts_add_svcs(s_services);
    if (ble_error != 0) return runtime_failure("GATT_ADD", ESP_FAIL);
    puts("BOOT_STAGE_GATT_OK");
    ble_hs_cfg.sync_cb = ble_on_sync;
    nimble_port_freertos_init(ble_host_task);
    s_tasks_started = true;
    if (xTaskCreate(dispatcher_task, "bmx_dispatch", 8192, NULL, 5, NULL) != pdPASS) return runtime_failure("DISPATCH_TASK", ESP_ERR_NO_MEM);
    if (xTaskCreate(notify_task, "bmx_notify", 4096, NULL, 5, NULL) != pdPASS) return runtime_failure("NOTIFY_TASK", ESP_ERR_NO_MEM);
    if (xTaskCreate(wifi_task, "bmx_wifi", 6144, NULL, 4, NULL) != pdPASS) return runtime_failure("WIFI_TASK", ESP_ERR_NO_MEM);
    puts("BOOT_STAGE_TASKS_OK");
    return ESP_OK;
}

void bootmux_ble_wifi_hid_loop(void) { vTaskDelay(pdMS_TO_TICKS(100)); }
