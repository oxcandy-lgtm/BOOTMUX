#pragma once

#include <stdint.h>
#include "tusb.h"

extern const tusb_desc_device_t bootmux_device_descriptor;
extern const uint8_t bootmux_hid_report_descriptor[];
extern const uint8_t bootmux_configuration_descriptor[];
extern const char *bootmux_string_descriptors[];
extern const uint8_t bootmux_string_descriptor_count;
