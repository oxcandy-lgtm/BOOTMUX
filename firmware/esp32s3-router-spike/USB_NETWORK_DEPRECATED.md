# USB Network Deprecation Notice

## Status: DISABLED BY DEFAULT

USB CDC-NCM Ethernet networking is **disabled by default** in all builds.

## Current Default (Safe Profile)
- USB CDC Serial only
- No NCM/ECM/RNDIS enumeration
- No DHCP server
- No automatic network interface creation on host

## Configuration Flag
```
CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL=n
```

## Removed Behaviors
The following are NOT active in the default build:
- `bootmux_usb_router_start()` at boot
- DHCP server start at boot
- USB network AUTOUP
- Always-up USB local recovery plane

## If USB Network Mode is Needed in Future
Create a separate build profile with these requirements:
- Default boot: serial only
- USB network activation: explicit physical button or serial reboot command
- Activation lifetime: bounded (auto-disable after timeout)
- DHCP server: disabled (manual IP only)
- Default gateway advertisement: impossible
- DNS advertisement: impossible
- IPv6 RA: disabled
- Automatic MAC service creation during normal boot: impossible

## bootmux_usb_router_stop() Requirements
When stopping USB network mode, the function must actually stop:
1. DHCP server
2. Link state
3. esp_netif
4. TinyUSB network function

Not just flip a flag - must actively tear down all network components.
