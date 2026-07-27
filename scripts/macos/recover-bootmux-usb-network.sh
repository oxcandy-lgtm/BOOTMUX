#!/bin/bash
set -euo pipefail

APPLY=0
if [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
elif [[ $# -ne 0 ]]; then
  echo "usage: $0 [--apply]" >&2
  exit 2
fi

wifi_device() {
  networksetup -listallhardwareports | awk '
    /^Hardware Port: (Wi-Fi|AirPort)$/ {
      getline
      sub(/^Device: /, "")
      print
      exit
    }
  '
}

service_for_device() {
  local wanted="$1"
  networksetup -listnetworkserviceorder | awk -v wanted="$wanted" '
    /^\([0-9]+\) / {
      service=$0
      sub(/^\([0-9]+\) /, "", service)
      next
    }
    /Device: / && index($0, "Device: " wanted ")") {
      print service
      exit
    }
  '
}

add_candidate() {
  local device="$1"
  [[ -n "$device" ]] || return 0
  for existing in "${CANDIDATES[@]:-}"; do
    [[ "$existing" == "$device" ]] && return 0
  done
  CANDIDATES+=("$device")
}

WIFI_DEVICE="$(wifi_device)"
[[ -n "$WIFI_DEVICE" ]] || {
  echo "Wi-Fi hardware device was not found." >&2
  exit 3
}

CANDIDATES=()
DEFAULT_GATEWAY="$(route -n get default 2>/dev/null | awk '/gateway:/{print $2; exit}')"
DEFAULT_INTERFACE="$(route -n get default 2>/dev/null | awk '/interface:/{print $2; exit}')"

if [[ "$DEFAULT_GATEWAY" == "10.77.0.1" ]]; then
  add_candidate "$DEFAULT_INTERFACE"
fi

for device in $(ifconfig -l); do
  address="$(ipconfig getifaddr "$device" 2>/dev/null || true)"
  case "$address" in
    10.77.0.*) add_candidate "$device" ;;
  esac
done

echo "BOOTMUX_USB_RECOVERY_AUDIT"
echo "wifi_device=$WIFI_DEVICE"
echo "default_gateway=${DEFAULT_GATEWAY:-none}"
echo "default_interface=${DEFAULT_INTERFACE:-none}"

if [[ ${#CANDIDATES[@]} -eq 0 ]]; then
  echo "candidate_usb_interfaces=none"
  echo "No active interface in 10.77.0.0/24 was found."
  echo "Connect the affected BOOTMUX S3, wait a few seconds, and run this script again."
  exit 4
fi

for device in "${CANDIDATES[@]}"; do
  service="$(service_for_device "$device")"
  address="$(ipconfig getifaddr "$device" 2>/dev/null || true)"
  echo "candidate_device=$device address=${address:-none} service=${service:-unknown}"
done

if [[ $APPLY -eq 0 ]]; then
  echo "No changes made. Re-run with --apply."
  exit 0
fi

for device in "${CANDIDATES[@]}"; do
  service="$(service_for_device "$device")"
  if [[ -n "$service" ]]; then
    echo "Disabling network service: $service ($device)"
    sudo networksetup -setnetworkserviceenabled "$service" off
  else
    echo "No macOS network service mapping for $device; bringing interface down only."
  fi
  sudo ifconfig "$device" down || true
done

if [[ "$DEFAULT_GATEWAY" == "10.77.0.1" ]]; then
  echo "Removing BOOTMUX-injected default route via 10.77.0.1"
  sudo route -n delete default 10.77.0.1 >/dev/null 2>&1 || true
fi

echo "Renewing Wi-Fi without deleting saved networks"
sudo networksetup -setairportpower "$WIFI_DEVICE" off
sleep 2
sudo networksetup -setairportpower "$WIFI_DEVICE" on
sleep 3
sudo ipconfig set "$WIFI_DEVICE" DHCP || true

NEW_GATEWAY="$(route -n get default 2>/dev/null | awk '/gateway:/{print $2; exit}')"
NEW_INTERFACE="$(route -n get default 2>/dev/null | awk '/interface:/{print $2; exit}')"

echo "BOOTMUX_USB_RECOVERY_RESULT"
echo "default_gateway=${NEW_GATEWAY:-none}"
echo "default_interface=${NEW_INTERFACE:-none}"

if [[ "$NEW_GATEWAY" == "10.77.0.1" ]]; then
  echo "FAIL: BOOTMUX default route is still active." >&2
  exit 5
fi

echo "PASS: BOOTMUX USB route removed; restart should not be required."
