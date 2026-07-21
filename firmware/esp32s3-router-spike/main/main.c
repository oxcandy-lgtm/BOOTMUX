#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "tinyusb.h"
#include "tinyusb_net.h"
#include "tusb.h"
#include "class/hid/hid.h"
#include "class/hid/hid_device.h"

#include "usb_descriptors.h"

static esp_err_t on_usb_packet(void *buffer, uint16_t length, void *context) {
    (void)buffer;
    (void)length;
    (void)context;
    return ESP_OK;
}

static void on_usb_tx_buffer_free(void *buffer, void *context) {
    (void)buffer;
    (void)context;
}

static void on_usb_network_ready(void *context) {
    (void)context;
    puts("BOOTMUX_USB_ETHERNET_READY");
}

static void send_ascii_probe(void) {
    uint8_t report[8] = {0};
    report[2] = HID_KEY_B;
    tud_hid_report(0, report, sizeof(report));
    vTaskDelay(pdMS_TO_TICKS(10));
    memset(report, 0, sizeof(report));
    tud_hid_report(0, report, sizeof(report));
    puts("BOOTMUX_HID_READY");
}

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

    const tinyusb_net_config_t net_config = {
        .mac_addr = {0x02, 0x42, 0x4f, 0x4f, 0x54, 0x01},
        .on_recv_callback = on_usb_packet,
        .free_tx_buffer = on_usb_tx_buffer_free,
        .on_init_callback = on_usb_network_ready,
        .user_context = NULL,
    };
    ESP_ERROR_CHECK(tinyusb_net_init(TINYUSB_USBDEV_0, &net_config));
    puts("BOOTMUX_ROUTER_SPIKE_STARTED");

    bool hid_probe_sent = false;
    while (true) {
        if (!hid_probe_sent && tud_mounted() && tud_hid_ready()) {
            send_ascii_probe();
            hid_probe_sent = true;
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
