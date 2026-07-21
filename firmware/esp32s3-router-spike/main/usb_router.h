#pragma once

#include "esp_err.h"

esp_err_t bootmux_usb_router_init(void);
esp_err_t bootmux_usb_router_enable_napt(void);
