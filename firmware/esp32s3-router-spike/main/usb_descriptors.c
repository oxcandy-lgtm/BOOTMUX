#include "usb_descriptors.h"

#include "class/hid/hid.h"
#include "class/hid/hid_device.h"
#include "tusb.h"

#define BOOTMUX_USB_VID 0x303A
#define BOOTMUX_USB_PID 0x4014

enum {
    BOOTMUX_ITF_HID = 0,
    BOOTMUX_ITF_NET,
    BOOTMUX_ITF_NET_DATA,
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
    BOOTMUX_EP_NET_NOTIFY = 0x82,
    BOOTMUX_EP_NET_OUT = 0x03,
    BOOTMUX_EP_NET_IN = 0x83,
};

const uint8_t bootmux_hid_report_descriptor[] = {
    TUD_HID_REPORT_DESC_KEYBOARD(),
};

const tusb_desc_device_t bootmux_device_descriptor = {
    .bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    .bDeviceClass = TUSB_CLASS_MISC,
    .bDeviceSubClass = MISC_SUBCLASS_COMMON,
    .bDeviceProtocol = MISC_PROTOCOL_IAD,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = BOOTMUX_USB_VID,
    .idProduct = BOOTMUX_USB_PID,
    .bcdDevice = 0x0100,
    .iManufacturer = BOOTMUX_STR_MANUFACTURER,
    .iProduct = BOOTMUX_STR_PRODUCT,
    .iSerialNumber = 0,
    .bNumConfigurations = 1,
};

const char *bootmux_string_descriptors[] = {
    (const char[]){0x09, 0x04},
    "BOOTMUX",
    "BOOTMUX Bridge",
    "BOOTMUX-R7A",
    "USB Ethernet",
    "020000000001",
};

const uint8_t bootmux_string_descriptor_count =
    sizeof(bootmux_string_descriptors) / sizeof(bootmux_string_descriptors[0]);

enum {
    BOOTMUX_CONFIG_TOTAL_LEN = TUD_CONFIG_DESC_LEN +
                               TUD_HID_DESC_LEN +
                               TUD_CDC_NCM_DESC_LEN,
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
};

const uint8_t *tud_hid_descriptor_report_cb(uint8_t instance) {
    (void)instance;
    return bootmux_hid_report_descriptor;
}
