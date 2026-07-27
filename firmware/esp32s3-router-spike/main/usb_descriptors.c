#include "usb_descriptors.h"

#include "class/hid/hid.h"
#include "class/hid/hid_device.h"
#include "tusb.h"

#ifndef CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL
#define CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL 0
#endif

#define BOOTMUX_USB_VID 0x303A
#define BOOTMUX_USB_PID 0x4014

#if CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL
#define BOOTMUX_USB_PRODUCT "BOOTMUX Bridge Experimental"
#define BOOTMUX_USB_SERIAL "BOOTMUX-R7A-NCM"
#define BOOTMUX_USB_DEVICE_CLASS TUSB_CLASS_MISC
#define BOOTMUX_USB_DEVICE_SUBCLASS MISC_SUBCLASS_COMMON
#define BOOTMUX_USB_DEVICE_PROTOCOL MISC_PROTOCOL_IAD
#else
#define BOOTMUX_USB_PRODUCT "BOOTMUX Keyboard Safe"
#define BOOTMUX_USB_SERIAL "BOOTMUX-HID-SAFE"
#define BOOTMUX_USB_DEVICE_CLASS 0x00
#define BOOTMUX_USB_DEVICE_SUBCLASS 0x00
#define BOOTMUX_USB_DEVICE_PROTOCOL 0x00
#endif

enum {
    BOOTMUX_ITF_HID = 0,
#if CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL
    BOOTMUX_ITF_NET,
    BOOTMUX_ITF_NET_DATA,
#endif
    BOOTMUX_ITF_TOTAL,
};

enum {
    BOOTMUX_STR_LANGID = 0,
    BOOTMUX_STR_MANUFACTURER,
    BOOTMUX_STR_PRODUCT,
    BOOTMUX_STR_SERIAL,
    BOOTMUX_STR_NET,
    BOOTMUX_STR_MAC,
};

enum {
    BOOTMUX_EP_HID = 0x81,
#if CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL
    BOOTMUX_EP_NET_NOTIFY = 0x82,
    BOOTMUX_EP_NET_OUT = 0x03,
    BOOTMUX_EP_NET_IN = 0x83,
#endif
};

const uint8_t bootmux_hid_report_descriptor[] = {
    TUD_HID_REPORT_DESC_KEYBOARD(),
};

const tusb_desc_device_t bootmux_device_descriptor = {
    .bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    .bDeviceClass = BOOTMUX_USB_DEVICE_CLASS,
    .bDeviceSubClass = BOOTMUX_USB_DEVICE_SUBCLASS,
    .bDeviceProtocol = BOOTMUX_USB_DEVICE_PROTOCOL,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = BOOTMUX_USB_VID,
    .idProduct = BOOTMUX_USB_PID,
    .bcdDevice = 0x0200,
    .iManufacturer = BOOTMUX_STR_MANUFACTURER,
    .iProduct = BOOTMUX_STR_PRODUCT,
    .iSerialNumber = BOOTMUX_STR_SERIAL,
    .bNumConfigurations = 1,
};

const char *bootmux_string_descriptors[] = {
    (const char[]){0x09, 0x04},
    "BOOTMUX",
    BOOTMUX_USB_PRODUCT,
    BOOTMUX_USB_SERIAL,
    "USB Ethernet Experimental",
    "020000000001",
};

const uint8_t bootmux_string_descriptor_count =
    sizeof(bootmux_string_descriptors) / sizeof(bootmux_string_descriptors[0]);

enum {
    BOOTMUX_CONFIG_TOTAL_LEN = TUD_CONFIG_DESC_LEN +
                               TUD_HID_DESC_LEN
#if CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL
                               + TUD_CDC_NCM_DESC_LEN
#endif
};

const uint8_t bootmux_configuration_descriptor[] = {
    TUD_CONFIG_DESCRIPTOR(
        1,
        BOOTMUX_ITF_TOTAL,
        0,
        BOOTMUX_CONFIG_TOTAL_LEN,
        TUSB_DESC_CONFIG_ATT_REMOTE_WAKEUP,
        100),
    TUD_HID_DESCRIPTOR(
        BOOTMUX_ITF_HID,
        0,
        HID_ITF_PROTOCOL_KEYBOARD,
        sizeof(bootmux_hid_report_descriptor),
        BOOTMUX_EP_HID,
        16,
        10),
#if CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL
    TUD_CDC_NCM_DESCRIPTOR(
        BOOTMUX_ITF_NET,
        BOOTMUX_STR_NET,
        BOOTMUX_STR_MAC,
        BOOTMUX_EP_NET_NOTIFY,
        64,
        BOOTMUX_EP_NET_OUT,
        BOOTMUX_EP_NET_IN,
        64,
        CFG_TUD_NET_MTU),
#endif
};

const uint8_t *tud_hid_descriptor_report_cb(uint8_t instance) {
    (void)instance;
    return bootmux_hid_report_descriptor;
}
