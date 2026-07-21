#pragma once

#include "esp_err.h"
#include "esp_netif.h"
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

esp_err_t bootmux_http_proxy_start(esp_netif_t *sta_netif, uint32_t epoch);
void bootmux_http_proxy_stop(void);
bool bootmux_http_proxy_is_ready(void);
bool bootmux_http_proxy_get_endpoint(char *buffer, size_t buffer_size);
