#pragma once

#include "esp_err.h"
#include "esp_netif.h"

esp_err_t bootmux_http_proxy_start(esp_netif_t *sta_netif);
void bootmux_http_proxy_stop(void);
