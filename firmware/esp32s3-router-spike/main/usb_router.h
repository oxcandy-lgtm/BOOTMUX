#pragma once

#include <stdbool.h>

#include "esp_err.h"

/*
 * BOOTMUX R7C-P1 S3 — USB router host-facing link authority.
 *
 * init() only creates the USB network class and the netif; it deliberately does
 * NOT start the netif.  The management-path gate is the sole owner of
 * start/stop and NAPT enable/disable, and calls them only while all four gate
 * conditions hold.  Every transition is idempotent and emits a fixed marker.
 *
 * In the safe HID-only profile (CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL unset)
 * every API is a side-effect-free stub: there is no USB network descriptor at
 * all, so nothing here can affect a host.
 */

esp_err_t bootmux_usb_router_init(void);

esp_err_t bootmux_usb_router_start(void);
esp_err_t bootmux_usb_router_stop(void);
esp_err_t bootmux_usb_router_enable_napt(void);
esp_err_t bootmux_usb_router_disable_napt(void);
bool bootmux_usb_router_is_started(void);
bool bootmux_usb_router_is_napt_enabled(void);
