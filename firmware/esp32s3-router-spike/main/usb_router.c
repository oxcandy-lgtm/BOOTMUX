#include "usb_router.h"

#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "esp_log.h"
#include "esp_netif.h"
#include "esp_netif_net_stack.h"
#include "freertos/FreeRTOS.h"
#include "lwip/inet.h"
#include "lwip/esp_netif_net_stack.h"
#include "tinyusb_net.h"

#define BOOTMUX_USB_IP ESP_IP4TOADDR(10, 77, 0, 1)
#define BOOTMUX_USB_NETMASK ESP_IP4TOADDR(255, 255, 255, 0)

static const char *TAG = "bootmux_usb_router";
static esp_netif_t *s_usb_netif;
static bool s_napt_enabled;
static uint8_t s_usb_mac[6] = {0x02, 0x42, 0x4f, 0x4f, 0x54, 0x01};

static void on_usb_ready(void *context) {
    (void)context;
    puts("BOOTMUX_USB_ETHERNET_READY");
}

static esp_err_t on_usb_receive(void *buffer, uint16_t length, void *context) {
    (void)context;
    if (!s_usb_netif || !buffer || length == 0) return ESP_ERR_INVALID_STATE;
    void *copy = malloc(length);
    if (!copy) return ESP_ERR_NO_MEM;
    memcpy(copy, buffer, length);
    esp_err_t error = esp_netif_receive(s_usb_netif, copy, length, NULL);
    if (error != ESP_OK) free(copy);
    return error;
}

static void on_usb_tx_buffer_free(void *buffer, void *context) {
    (void)buffer;
    (void)context;
}

static esp_err_t usb_netif_transmit(void *handle, void *buffer, size_t length) {
    (void)handle;
    return tinyusb_net_send_sync(buffer, (uint16_t)length, NULL, pdMS_TO_TICKS(100));
}

static void usb_netif_free_rx_buffer(void *handle, void *buffer) {
    (void)handle;
    free(buffer);
}

esp_err_t bootmux_usb_router_init(void) {
    const tinyusb_net_config_t net_config = {
        .mac_addr = {0x02, 0x42, 0x4f, 0x4f, 0x54, 0x01},
        .on_recv_callback = on_usb_receive,
        .free_tx_buffer = on_usb_tx_buffer_free,
        .on_init_callback = on_usb_ready,
        .user_context = NULL,
    };
    esp_err_t error = tinyusb_net_init(TINYUSB_USBDEV_0, &net_config);
    if (error != ESP_OK) return error;

    static esp_netif_ip_info_t ip_info = {
        .ip = { .addr = BOOTMUX_USB_IP },
        .gw = { .addr = BOOTMUX_USB_IP },
        .netmask = { .addr = BOOTMUX_USB_NETMASK },
    };
    static esp_netif_inherent_config_t base_config = {
        .flags = ESP_NETIF_DHCP_SERVER | ESP_NETIF_FLAG_AUTOUP,
        .ip_info = &ip_info,
        .if_key = "usb",
        .if_desc = "BOOTMUX USB Ethernet",
        .route_prio = 10,
    };
    static esp_netif_driver_ifconfig_t driver_config = {
        .handle = (void *)1,
        .transmit = usb_netif_transmit,
        .driver_free_rx_buffer = usb_netif_free_rx_buffer,
    };
    static struct esp_netif_netstack_config stack_config = {
        .lwip = {
            .init_fn = ethernetif_init,
            .input_fn = ethernetif_input,
        },
    };
    const esp_netif_config_t netif_config = {
        .base = &base_config,
        .driver = &driver_config,
        .stack = &stack_config,
    };
    s_usb_netif = esp_netif_new(&netif_config);
    if (!s_usb_netif) return ESP_ERR_NO_MEM;
    memcpy(s_usb_mac, net_config.mac_addr, sizeof(s_usb_mac));
    error = esp_netif_set_mac(s_usb_netif, s_usb_mac);
    if (error != ESP_OK) return error;
    esp_netif_action_start(s_usb_netif, 0, 0, 0);
    puts("BOOTMUX_USB_NETIF_READY");
    puts("BOOTMUX_USB_LAN_READY");
    return ESP_OK;
}

esp_err_t bootmux_usb_router_enable_napt(void) {
    if (s_napt_enabled) return ESP_OK;
    if (!s_usb_netif) return ESP_ERR_INVALID_STATE;
    esp_err_t error = esp_netif_napt_enable(s_usb_netif);
    if (error == ESP_OK) puts("BOOTMUX_NAPT_READY");
    else ESP_LOGE(TAG, "NAPT enable failed code=%s", esp_err_to_name(error));
    if (error == ESP_OK) s_napt_enabled = true;
    return error;
}
