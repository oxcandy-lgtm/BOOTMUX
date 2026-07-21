#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "tinyusb.h"
#include "tusb.h"
#include "class/hid/hid.h"
#include "class/hid/hid_device.h"

#include "usb_descriptors.h"
#include "ble_wifi_runtime.h"

#ifndef CONFIG_BOOTMUX_R7A_HID_PROBE
#define CONFIG_BOOTMUX_R7A_HID_PROBE 0
#endif

#if CONFIG_BOOTMUX_R7A_HID_PROBE
static void send_ascii_probe(void) {
    uint8_t report[8] = {0};
    report[2] = HID_KEY_B;
    tud_hid_report(0, report, sizeof(report));
    vTaskDelay(pdMS_TO_TICKS(10));
    memset(report, 0, sizeof(report));
    tud_hid_report(0, report, sizeof(report));
    puts("BOOTMUX_HID_READY");
}
#endif

uint16_t tud_hid_get_report_cb(uint8_t instance, uint8_t report_id,
                               hid_report_type_t report_type, uint8_t *buffer,
                               uint16_t reqlen) {
    (void)instance;
    (void)report_id;
    (void)report_type;
    (void)buffer;
    (void)reqlen;
    return 0;
}

void tud_hid_set_report_cb(uint8_t instance, uint8_t report_id,
                           hid_report_type_t report_type,
                           uint8_t const *buffer, uint16_t bufsize) {
    (void)instance;
    (void)report_id;
    (void)report_type;
    (void)buffer;
    (void)bufsize;
}

void app_main(void) {
    puts("BOOT_STAGE_APP_START");
    const tinyusb_config_t usb_config = {
        .device_descriptor = &bootmux_device_descriptor,
        .string_descriptor = bootmux_string_descriptors,
        .string_descriptor_count = bootmux_string_descriptor_count,
        .external_phy = false,
        .configuration_descriptor = bootmux_configuration_descriptor,
        .self_powered = false,
        .vbus_monitor_io = -1,
    };
    ESP_ERROR_CHECK(tinyusb_driver_install(&usb_config));
    puts("BOOT_STAGE_USB_OK");

    esp_err_t runtime_error = bootmux_ble_wifi_init();
    if (runtime_error == ESP_OK) {
        puts("BOOTMUX_RUNTIME_READY");
    } else {
        printf("BOOTMUX_RUNTIME_FAILED code=%s\n", esp_err_to_name(runtime_error));
    }
    puts("BOOTMUX_ROUTER_SPIKE_STARTED");

#if CONFIG_BOOTMUX_R7A_HID_PROBE
    bool hid_probe_sent = false;
#endif
    while (true) {
#if CONFIG_BOOTMUX_R7A_HID_PROBE
        if (!hid_probe_sent && tud_mounted() && tud_hid_ready()) {
            send_ascii_probe();
            hid_probe_sent = true;
        }
#endif
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
