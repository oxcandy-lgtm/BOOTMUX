idf_component_register(
    SRCS "main.c" "usb_descriptors.c" "ble_wifi_runtime.c"
    INCLUDE_DIRS "."
    REQUIRES esp_tinyusb bt esp_wifi esp_event esp_netif nvs_flash json mbedtls
)

target_include_directories(${COMPONENT_LIB} PRIVATE
    "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/nimble/include"
    "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/nimble/host/include"
    "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/nimble/host/services/gap/include"
    "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/nimble/host/services/gatt/include"
    "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/porting/nimble/include"
    "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/porting/npl/freertos/include"
    "$ENV{IDF_PATH}/components/bt/host/nimble/port/include"
    "$ENV{IDF_PATH}/components/bt/host/nimble/esp-hci/include"
    "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/nimble/transport/include"
    "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/nimble/host/util/include"
)
