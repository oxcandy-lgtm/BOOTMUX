#include "http_connect_proxy.h"

#include <ctype.h>
#include <errno.h>
#include <netdb.h>
#include <stdio.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lwip/inet.h"

#define BOOTMUX_PROXY_PORT 3128
#define BOOTMUX_PROXY_HEADER_MAX 4096
#define BOOTMUX_PROXY_BUFFER 4096
#define BOOTMUX_PROXY_IDLE_SECONDS 300
#define BOOTMUX_PROXY_CONNECT_SECONDS 15
#define BOOTMUX_PROXY_MAX_CLIENTS 1

static TaskHandle_t s_proxy_task;
static volatile bool s_proxy_stop;
static int s_listen_fd = -1;
static int s_client_fd = -1;
static uint32_t s_connection_id;
static uint32_t s_bound_address;

static void close_fd(int *fd) {
    if (*fd >= 0) {
        shutdown(*fd, SHUT_RDWR);
        close(*fd);
        *fd = -1;
    }
}

static bool has_control(const char *value, size_t length) {
    for (size_t i = 0; i < length; ++i) if ((unsigned char)value[i] < 0x20 || value[i] == 0x7f) return true;
    return false;
}

static bool parse_connect(const char *header, size_t length, char *host, size_t host_size) {
    const char *line_end = strstr(header, "\r\n");
    if (!line_end || strncmp(header, "CONNECT ", 8) != 0) return false;
    const char *authority = header + 8;
    const char *space = memchr(authority, ' ', (size_t)(line_end - authority));
    if (!space || space == authority || (size_t)(space - authority) >= host_size) return false;
    size_t authority_len = (size_t)(space - authority);
    if (has_control(authority, authority_len) || memchr(authority, '@', authority_len)) return false;
    if (authority[0] == '[' || memchr(authority, '[', authority_len) || memchr(authority, ']', authority_len)) return false;
    const char *colon = memrchr(authority, ':', authority_len);
    if (!colon || colon == authority || strncmp(colon + 1, "443", (size_t)(space - colon - 1)) != 0 || (size_t)(space - colon - 1) != 3) return false;
    memcpy(host, authority, (size_t)(colon - authority));
    host[colon - authority] = 0;
    return host[0] != 0;
}

static bool recv_header(int fd, char *header, size_t *length) {
    *length = 0;
    while (*length + 1 < BOOTMUX_PROXY_HEADER_MAX) {
        ssize_t received = recv(fd, header + *length, 1, 0);
        if (received != 1) return false;
        *length += 1;
        header[*length] = 0;
        if (*length >= 4 && strstr(header, "\r\n\r\n")) return true;
    }
    return false;
}

static bool send_all(int fd, const void *data, size_t length) {
    const uint8_t *cursor = data;
    while (length > 0) {
        ssize_t sent = send(fd, cursor, length, 0);
        if (sent <= 0) return false;
        cursor += sent;
        length -= (size_t)sent;
    }
    return true;
}

static void relay(int client, int upstream) {
    uint8_t buffer[BOOTMUX_PROXY_BUFFER];
    int64_t last_activity = esp_timer_get_time() / 1000000;
    while (!s_proxy_stop) {
        fd_set read_set;
        FD_ZERO(&read_set);
        FD_SET(client, &read_set);
        FD_SET(upstream, &read_set);
        int max_fd = client > upstream ? client : upstream;
        struct timeval timeout = {.tv_sec = 1, .tv_usec = 0};
        int ready = select(max_fd + 1, &read_set, NULL, NULL, &timeout);
        if (ready < 0) break;
        if (ready == 0) {
            if ((esp_timer_get_time() / 1000000) - last_activity >= BOOTMUX_PROXY_IDLE_SECONDS) break;
            continue;
        }
        int from = FD_ISSET(client, &read_set) ? client : upstream;
        int to = from == client ? upstream : client;
        ssize_t received = recv(from, buffer, sizeof(buffer), 0);
        if (received <= 0 || !send_all(to, buffer, (size_t)received)) break;
        last_activity = esp_timer_get_time() / 1000000;
    }
}

static void handle_client(int client, uint32_t connection_id) {
    char header[BOOTMUX_PROXY_HEADER_MAX];
    size_t header_length = 0;
    char host[256];
    struct timeval io_timeout = {.tv_sec = BOOTMUX_PROXY_CONNECT_SECONDS, .tv_usec = 0};
    setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &io_timeout, sizeof(io_timeout));
    setsockopt(client, SOL_SOCKET, SO_SNDTIMEO, &io_timeout, sizeof(io_timeout));
    if (!recv_header(client, header, &header_length)) {
        printf("S3_PROXY_CLOSE id=%lu reason=header_read_failed\n", (unsigned long)connection_id);
        static const char response[] = "HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n";
        (void)send_all(client, response, sizeof(response) - 1);
        return;
    }
    printf("S3_PROXY_HEADER_COMPLETE id=%lu bytes=%u\n", (unsigned long)connection_id,
           (unsigned)header_length);
    if (!parse_connect(header, header_length, host, sizeof(host))) {
        printf("S3_PROXY_CLOSE id=%lu reason=connect_parse_failed\n", (unsigned long)connection_id);
        static const char response[] = "HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n";
        (void)send_all(client, response, sizeof(response) - 1);
        return;
    }
    puts("S3_PROXY_CONNECT_PARSE_OK");
    struct addrinfo hints = {.ai_family = AF_INET, .ai_socktype = SOCK_STREAM};
    struct addrinfo *result = NULL;
    if (getaddrinfo(host, "443", &hints, &result) != 0 || !result) {
        printf("S3_PROXY_CLOSE id=%lu reason=dns_failed\n", (unsigned long)connection_id);
        static const char response[] = "HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n";
        (void)send_all(client, response, sizeof(response) - 1);
        if (result) freeaddrinfo(result);
        return;
    }
    puts("S3_PROXY_DNS_OK");
    int upstream = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if (upstream >= 0) {
        setsockopt(upstream, SOL_SOCKET, SO_RCVTIMEO, &io_timeout, sizeof(io_timeout));
        setsockopt(upstream, SOL_SOCKET, SO_SNDTIMEO, &io_timeout, sizeof(io_timeout));
    }
    bool connected = upstream >= 0 && connect(upstream, result->ai_addr, result->ai_addrlen) == 0;
    freeaddrinfo(result);
    if (!connected) {
        printf("S3_PROXY_CLOSE id=%lu reason=upstream_connect_failed\n", (unsigned long)connection_id);
        close_fd(&upstream);
        static const char response[] = "HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n";
        (void)send_all(client, response, sizeof(response) - 1);
        return;
    }
    puts("S3_PROXY_UPSTREAM_CONNECTED");
    static const char established[] = "HTTP/1.1 200 Connection Established\r\n\r\n";
    if (!send_all(client, established, sizeof(established) - 1)) {
        printf("S3_PROXY_CLOSE id=%lu reason=success_response_failed\n", (unsigned long)connection_id);
        close_fd(&upstream);
        return;
    }
    printf("S3_PROXY_200_SENT id=%lu\n", (unsigned long)connection_id);
    printf("S3_PROXY_RELAY_START id=%lu\n", (unsigned long)connection_id);
    relay(client, upstream);
    close_fd(&upstream);
    printf("S3_PROXY_CLOSE id=%lu reason=relay_done\n", (unsigned long)connection_id);
}

static void proxy_task(void *arg) {
    uint32_t address = (uint32_t)(uintptr_t)arg;
    s_listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (s_listen_fd < 0) goto done;
    int reuse = 1;
    setsockopt(s_listen_fd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
    struct sockaddr_in local = {.sin_family = AF_INET, .sin_port = htons(BOOTMUX_PROXY_PORT), .sin_addr.s_addr = address};
    if (bind(s_listen_fd, (struct sockaddr *)&local, sizeof(local)) != 0) {
        puts("S3_PROXY_CLOSE reason=bind_failed");
        goto done;
    }
    if (listen(s_listen_fd, BOOTMUX_PROXY_MAX_CLIENTS) != 0) {
        puts("S3_PROXY_CLOSE reason=listen_failed");
        goto done;
    }
    puts("BOOTMUX_PROXY_READY");
    puts("S3_PROXY_ACCEPT_READY");
    while (!s_proxy_stop) {
        struct timeval timeout = {.tv_sec = 1, .tv_usec = 0};
        fd_set set;
        FD_ZERO(&set);
        FD_SET(s_listen_fd, &set);
        if (select(s_listen_fd + 1, &set, NULL, NULL, &timeout) <= 0) continue;
        s_client_fd = accept(s_listen_fd, NULL, NULL);
        if (s_client_fd < 0) continue;
        uint32_t connection_id = ++s_connection_id;
        printf("S3_PROXY_ACCEPT id=%lu\n", (unsigned long)connection_id);
        handle_client(s_client_fd, connection_id);
        close_fd(&s_client_fd);
        printf("S3_PROXY_CLOSE id=%lu reason=client_done\n", (unsigned long)connection_id);
        puts("S3_PROXY_ACCEPT_READY");
    }
done:
    close_fd(&s_client_fd);
    close_fd(&s_listen_fd);
    s_proxy_task = NULL;
    vTaskDelete(NULL);
}

esp_err_t bootmux_http_proxy_start(esp_netif_t *sta_netif, uint32_t epoch) {
    (void)epoch;
    if (!sta_netif || s_proxy_task) return ESP_ERR_INVALID_STATE;
    esp_netif_ip_info_t info;
    esp_err_t error = esp_netif_get_ip_info(sta_netif, &info);
    if (error != ESP_OK || info.ip.addr == 0) return ESP_ERR_INVALID_STATE;
    s_proxy_stop = false;
    s_bound_address = info.ip.addr;
    if (xTaskCreate(proxy_task, "bmx_proxy", 8192, (void *)(uintptr_t)info.ip.addr, 5, &s_proxy_task) != pdPASS) return ESP_ERR_NO_MEM;
    for (int attempt = 0; attempt < 200; ++attempt) {
        if (bootmux_http_proxy_is_ready()) return ESP_OK;
        vTaskDelay(pdMS_TO_TICKS(10));
    }
    bootmux_http_proxy_stop();
    return ESP_ERR_TIMEOUT;
}

void bootmux_http_proxy_stop(void) {
    s_proxy_stop = true;
    close_fd(&s_client_fd);
    close_fd(&s_listen_fd);
    for (int attempt = 0; s_proxy_task && attempt < 100; ++attempt) vTaskDelay(pdMS_TO_TICKS(10));
    s_bound_address = 0;
}

bool bootmux_http_proxy_is_ready(void) {
    return s_proxy_task != NULL && s_listen_fd >= 0 && s_bound_address != 0;
}

bool bootmux_http_proxy_get_endpoint(char *buffer, size_t buffer_size) {
    if (!buffer || buffer_size == 0 || !bootmux_http_proxy_is_ready()) return false;
    struct in_addr address = {.s_addr = s_bound_address};
    const char *text = inet_ntoa(address);
    if (!text || snprintf(buffer, buffer_size, "%s:%u", text, BOOTMUX_PROXY_PORT) >= (int)buffer_size) return false;
    return true;
}
