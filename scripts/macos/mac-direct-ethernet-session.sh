#!/usr/bin/env bash
# mac-direct-ethernet-session.sh
# One-shot direct ethernet session manager for AX88179B adapter
# NO background processes, NO Wi-Fi mutations, NO persistent daemons
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STATE_DIR="${STATE_DIR:-/tmp/mac-direct-ethernet-session}"
BACKUP_FILE="$STATE_DIR/ax88179b-backup.json"

# === READ-ONLY Wi-Fi Identification ===
identify_wifi() {
    local output
    output="$(networksetup -listallhardwareports)"
    local wifi_if
    wifi_if="$(echo "$output" | awk '
        /Hardware Port: Wi-Fi/ { found=1 }
        found && /Device: / { print $2; exit }
    ')"
    if [[ -z "$wifi_if" ]]; then
        echo "ERROR: Could not identify Wi-Fi interface" >&2
        exit 1
    fi
    echo "$wifi_if"
}

# === READ-ONLY Default Route ===
get_default_route() {
    local default_if
    default_if="$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')"
    if [[ -z "$default_if" ]]; then
        echo "ERROR: Could not determine default route interface" >&2
        exit 1
    fi
    echo "$default_if"
}

# === AX88179B Discovery ===
discover_ax88179b() {
    local usb_data
    usb_data="$(system_profiler SPUSBDataType 2>/dev/null)"

    local candidates=()
    local found_ax=false
    local current_mac=""

    # Parse system_profiler for AX88179B (VID 0b95, PID 1790/1793)
    while IFS= read -r line; do
        if echo "$line" | grep -qi "AX88179B\|0b95.*1790\|0b95.*1793"; then
            found_ax=true
        fi
        if echo "$line" | grep -qi "Ethernet Address:\|MAC Address:"; then
            current_mac="$(echo "$line" | grep -oE '([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}' | head -1)"
            if $found_ax && [[ -n "$current_mac" ]]; then
                candidates+=("$current_mac")
                found_ax=false
                current_mac=""
            fi
        fi
    done <<< "$usb_data"

    # Fallback: awk-based extraction
    if [[ ${#candidates[@]} -eq 0 ]]; then
        local mac_from_profiler
        mac_from_profiler="$(system_profiler SPUSBDataType 2>/dev/null | awk '
            /AX88179/ { found=1 }
            found && /[Ee]thernet [Aa]ddress/ {
                match($0, /[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}/)
                if (RLENGTH > 0) { print substr($0, RSTART, RLENGTH); found=0 }
            }
        ')"
        if [[ -n "$mac_from_profiler" ]]; then
            while IFS= read -r mac; do
                [[ -n "$mac" ]] && candidates+=("$mac")
            done <<< "$mac_from_profiler"
        fi
    fi

    if [[ ${#candidates[@]} -eq 0 ]]; then
        echo "ERROR: No AX88179B adapter found via USB profiler" >&2
        exit 1
    fi

    if [[ ${#candidates[@]} -gt 1 ]]; then
        local unique_macs
        unique_macs="$(printf '%s\n' "${candidates[@]}" | sort -u | wc -l)"
        if [[ "$unique_macs" -gt 1 ]]; then
            echo "ERROR: Multiple AX88179B adapters found - cannot uniquely identify" >&2
            echo "Found MACs: ${candidates[*]}" >&2
            exit 1
        fi
    fi

    local target_mac="${candidates[0]}"

    # Find network interface matching this MAC
    local eth_if=""
    for iface in $(ifconfig -l); do
        local if_mac
        if_mac="$(ifconfig "$iface" 2>/dev/null | grep -oE 'ether [0-9a-f:]+' | awk '{print $2}' || true)"
        if [[ -n "$if_mac" && "${if_mac,,}" == "${target_mac,,}" ]]; then
            eth_if="$iface"
            break
        fi
    done

    if [[ -z "$eth_if" ]]; then
        echo "ERROR: Could not map MAC $target_mac to a network interface" >&2
        exit 1
    fi

    # Find network service name for this interface
    local eth_service=""
    local svc_list
    svc_list="$(networksetup -listallnetworkservices)"
    local hw_ports
    hw_ports="$(networksetup -listallhardwareports)"

    # Match by hardware port device name
    while IFS= read -r svc; do
        [[ "$svc" == *"denotes"* ]] && continue
        [[ -z "$svc" ]] && continue
        local port_dev
        port_dev="$(echo "$hw_ports" | awk -v port="$svc" '
            index($0, "Hardware Port: " port) { found=1 }
            found && /Device:/ { print $2; found=0; exit }
        ')"
        if [[ "$port_dev" == "$eth_if" ]]; then
            eth_service="$svc"
            break
        fi
    done <<< "$svc_list"

    # Fallback: match by service name containing AX88179 or USB Ethernet
    if [[ -z "$eth_service" ]]; then
        while IFS= read -r svc; do
            [[ "$svc" == *"denotes"* ]] && continue
            [[ -z "$svc" ]] && continue
            if echo "$svc" | grep -qi "AX88179\|USB.*Ethernet"; then
                eth_service="$svc"
                break
            fi
        done <<< "$svc_list"
    fi

    if [[ -z "$eth_service" ]]; then
        echo "ERROR: Could not find network service for interface $eth_if (MAC: $target_mac)" >&2
        exit 1
    fi

    jq -n \
        --arg service "$eth_service" \
        --arg interface "$eth_if" \
        --arg mac "$target_mac" \
        '{service: $service, interface: $interface, mac: $mac}'
}

# === Backup AX88179B Config ===
backup_config() {
    local service="$1"

    local ipv4_info
    ipv4_info="$(networksetup -getinfo "$service" 2>/dev/null || echo "")"

    local ipv4_mode="DHCP"
    local ipv4_addr="" ipv4_mask="" ipv4_router=""
    if echo "$ipv4_info" | grep -q "Manual Configuration"; then
        ipv4_mode="Manual"
        ipv4_addr="$(echo "$ipv4_info" | awk '/^IP address:/{print $3}')"
        ipv4_mask="$(echo "$ipv4_info" | awk '/^Subnet mask:/{print $3}')"
        ipv4_router="$(echo "$ipv4_info" | awk '/^Router:/{print $2}')"
    elif echo "$ipv4_info" | grep -q "DHCP Configuration"; then
        ipv4_mode="DHCP"
        ipv4_addr="$(echo "$ipv4_info" | awk '/^IP address:/{print $3}')"
        ipv4_mask="$(echo "$ipv4_info" | awk '/^Subnet mask:/{print $3}')"
        ipv4_router="$(echo "$ipv4_info" | awk '/^Router:/{print $2}')"
    fi

    local ipv6_mode
    ipv6_mode="$(networksetup -getv6 "$service" 2>/dev/null | head -1 || echo 'Automatic')"
    ipv6_mode="$(echo "$ipv6_mode" | awk -F': ' '{print $2}')"
    [[ -z "$ipv6_mode" ]] && ipv6_mode="Automatic"

    local dns_servers
    dns_servers="$(networksetup -getdnsservers "$service" 2>/dev/null || echo "")"
    local dns_array="[]"
    if [[ -n "$dns_servers" && "$dns_servers" != *"There aren"* ]]; then
        dns_array="$(echo "$dns_servers" | jq -R -s 'split("\n") | map(select(length > 0))')"
    fi

    local search_domains
    search_domains="$(networksetup -getsearchdomains "$service" 2>/dev/null || echo "")"
    local domains_array="[]"
    if [[ -n "$search_domains" && "$search_domains" != *"There aren"* ]]; then
        domains_array="$(echo "$search_domains" | jq -R -s 'split("\n") | map(select(length > 0))')"
    fi

    local web_proxy="off" secure_proxy="off" socks_proxy="off" auto_proxy="off"
    local web_info secure_info socks_info auto_info
    web_info="$(networksetup -getwebproxy "$service" 2>/dev/null || echo "")"
    secure_info="$(networksetup -getsecurewebproxy "$service" 2>/dev/null || echo "")"
    socks_info="$(networksetup -getsocksfirewallproxy "$service" 2>/dev/null || echo "")"
    auto_info="$(networksetup -getautoproxyurl "$service" 2>/dev/null || echo "")"

    echo "$web_info" | grep -qi "Enabled: Yes" && web_proxy="on"
    echo "$secure_info" | grep -qi "Enabled: Yes" && secure_proxy="on"
    echo "$socks_info" | grep -qi "Enabled: Yes" && socks_proxy="on"
    echo "$auto_info" | grep -qi "Enabled: Yes" && auto_proxy="on"

    jq -n \
        --arg service "$service" \
        --arg ipv4_mode "$ipv4_mode" \
        --arg ipv4_addr "$ipv4_addr" \
        --arg ipv4_mask "$ipv4_mask" \
        --arg ipv4_router "$ipv4_router" \
        --arg ipv6_mode "$ipv6_mode" \
        --argjson dns_servers "$dns_array" \
        --argjson search_domains "$domains_array" \
        --arg web_proxy "$web_proxy" \
        --arg secure_proxy "$secure_proxy" \
        --arg socks_proxy "$socks_proxy" \
        --arg auto_proxy "$auto_proxy" \
        '{
            service: $service,
            ipv4: {
                mode: $ipv4_mode,
                address: $ipv4_addr,
                mask: $ipv4_mask,
                router: $ipv4_router
            },
            ipv6: {
                mode: $ipv6_mode
            },
            dns: {
                servers: $dns_servers,
                search_domains: $search_domains
            },
            proxies: {
                web: $web_proxy,
                secure: $secure_proxy,
                socks: $socks_proxy,
                auto: $auto_proxy
            }
        }' > "$BACKUP_FILE"

    echo "Backup saved to $BACKUP_FILE"
}

# === Apply Direct Ethernet Settings ===
apply_settings() {
    local service="$1"
    networksetup -setmanual "$service" 192.168.11.2 255.255.255.0
    networksetup -setv6off "$service"
    networksetup -setdnsservers "$service" empty
    networksetup -setsearchdomains "$service" empty
    networksetup -setwebproxystate "$service" off
    networksetup -setsecurewebproxystate "$service" off
    networksetup -setsocksfirewallproxystate "$service" off
    networksetup -setautoproxystate "$service" off
    networksetup -setproxyautodiscovery "$service" off
    echo "Applied direct ethernet settings to: $service"
}

# === Cheap Postcondition Check ===
verify_postcondition() {
    local wifi_if="$1"
    local eth_if="$2"
    local eth_service="$3"

    local ok=true

    local current_default
    current_default="$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')"
    if [[ "$current_default" != "$wifi_if" ]]; then
        echo "FAIL: Default route is on $current_default, expected $wifi_if" >&2
        ok=false
    fi

    local eth_info
    eth_info="$(networksetup -getinfo "$eth_service" 2>/dev/null || echo "")"
    if ! echo "$eth_info" | grep -q "192.168.11.2"; then
        echo "FAIL: Ethernet IP is not 192.168.11.2" >&2
        ok=false
    fi

    local eth_router
    eth_router="$(echo "$eth_info" | awk '/^Router:/{print $2}')"
    if [[ -n "$eth_router" && "$eth_router" != "none" && "$eth_router" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "WARN: Ethernet has router set: $eth_router" >&2
    fi

    local current_wifi
    current_wifi="$(identify_wifi)"
    if [[ "$current_wifi" != "$wifi_if" ]]; then
        echo "FAIL: Wi-Fi interface changed from $wifi_if to $current_wifi" >&2
        ok=false
    fi

    if ! $ok; then
        echo "Postcondition verification FAILED" >&2
        exit 1
    fi

    echo "Postcondition check: PASS"
}

# === Subcommand: prepare ===
cmd_prepare() {
    echo "=== prepare ==="
    local wifi_if
    wifi_if="$(identify_wifi)"
    echo "Wi-Fi interface: $wifi_if"

    local default_if
    default_if="$(get_default_route)"
    echo "Default route interface: $default_if"

    if [[ "$default_if" != "$wifi_if" ]]; then
        echo "ERROR: Default route is not on Wi-Fi interface" >&2
        exit 1
    fi

    local eth_info
    eth_info="$(discover_ax88179b)"
    local eth_service eth_if eth_mac
    eth_service="$(echo "$eth_info" | jq -r .service)"
    eth_if="$(echo "$eth_info" | jq -r .interface)"
    eth_mac="$(echo "$eth_info" | jq -r .mac)"
    echo "AX88179B: service=$eth_service interface=$eth_if mac=$eth_mac"

    mkdir -p "$STATE_DIR"

    # Idempotent: if backup already exists, skip re-backup
    if [[ -f "$BACKUP_FILE" ]]; then
        echo "Backup already exists at $BACKUP_FILE (skipping re-backup for idempotency)"
    else
        backup_config "$eth_service"
    fi

    apply_settings "$eth_service"
    verify_postcondition "$wifi_if" "$eth_if" "$eth_service"

    echo "=== prepare complete ==="
}

# === Subcommand: check ===
cmd_check() {
    echo "=== check ==="
    local wifi_if eth_info eth_service eth_if
    wifi_if="$(identify_wifi)"
    eth_info="$(discover_ax88179b)"
    eth_service="$(echo "$eth_info" | jq -r .service)"
    eth_if="$(echo "$eth_info" | jq -r .interface)"

    local default_if
    default_if="$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')"

    echo "default_route_interface: $default_if"
    echo "wifi_interface: $wifi_if"
    echo "ethernet_interface: $eth_if"

    local ipv4_info
    ipv4_info="$(networksetup -getinfo "$eth_service")"
    echo "ethernet_config:"
    echo "$ipv4_info"

    local v6_mode
    v6_mode="$(networksetup -getv6 "$eth_service" 2>/dev/null || echo 'unknown')"
    echo "ethernet_ipv6: $v6_mode"

    local dns_info
    dns_info="$(networksetup -getdnsservers "$eth_service" 2>/dev/null || echo 'none')"
    echo "ethernet_dns: $dns_info"

    local ok=true
    [[ "$default_if" == "$wifi_if" ]] || { echo "FAIL: default route not on wifi"; ok=false; }
    echo "$ipv4_info" | grep -q "192.168.11.2" || { echo "FAIL: ethernet IP not 192.168.11.2"; ok=false; }
    echo "$ipv4_info" | grep -q "Router: none\|Router: " && echo "$ipv4_info" | grep -qv "Router: [0-9]" || { echo "WARN: ethernet has router set"; }

    if $ok; then
        echo "=== check: PASS ==="
    else
        echo "=== check: FAIL ==="
        exit 1
    fi
}

# === Subcommand: restore ===
cmd_restore() {
    echo "=== restore ==="
    if [[ ! -f "$BACKUP_FILE" ]]; then
        echo "ERROR: No backup found at $BACKUP_FILE" >&2
        exit 1
    fi

    local eth_service
    eth_service="$(jq -r .service "$BACKUP_FILE")"

    # Restore IPv4
    local ipv4_mode ipv4_addr ipv4_mask ipv4_router
    ipv4_mode="$(jq -r .ipv4.mode "$BACKUP_FILE")"
    if [[ "$ipv4_mode" == "DHCP" ]]; then
        networksetup -setdhcp "$eth_service"
    elif [[ "$ipv4_mode" == "Manual" ]]; then
        ipv4_addr="$(jq -r .ipv4.address "$BACKUP_FILE")"
        ipv4_mask="$(jq -r .ipv4.mask "$BACKUP_FILE")"
        ipv4_router="$(jq -r .ipv4.router "$BACKUP_FILE")"
        if [[ -n "$ipv4_router" && "$ipv4_router" != "null" ]]; then
            networksetup -setmanual "$eth_service" "$ipv4_addr" "$ipv4_mask" "$ipv4_router"
        else
            networksetup -setmanual "$eth_service" "$ipv4_addr" "$ipv4_mask"
        fi
    fi

    # Restore IPv6
    local ipv6_mode
    ipv6_mode="$(jq -r .ipv6.mode "$BACKUP_FILE")"
    if [[ "$ipv6_mode" == "Automatic" ]]; then
        networksetup -setv6automatic "$eth_service"
    elif [[ "$ipv6_mode" == "Off" ]]; then
        networksetup -setv6off "$eth_service"
    fi

    # Restore DNS
    local dns
    dns="$(jq -r '.dns.servers[]?' "$BACKUP_FILE" | tr '\n' ' ')"
    if [[ -n "$dns" ]]; then
        networksetup -setdnsservers "$eth_service" $dns
    else
        networksetup -setdnsservers "$eth_service" empty
    fi

    # Restore search domains
    local domains
    domains="$(jq -r '.dns.search_domains[]?' "$BACKUP_FILE" | tr '\n' ' ')"
    if [[ -n "$domains" ]]; then
        networksetup -setsearchdomains "$eth_service" $domains
    else
        networksetup -setsearchdomains "$eth_service" empty
    fi

    # Restore proxies
    local web_proxy secure_proxy socks_proxy auto_proxy
    web_proxy="$(jq -r .proxies.web "$BACKUP_FILE")"
    secure_proxy="$(jq -r .proxies.secure "$BACKUP_FILE")"
    socks_proxy="$(jq -r .proxies.socks "$BACKUP_FILE")"
    auto_proxy="$(jq -r .proxies.auto "$BACKUP_FILE")"
    [[ "$web_proxy" == "on" ]] && networksetup -setwebproxystate "$eth_service" on || networksetup -setwebproxystate "$eth_service" off
    [[ "$secure_proxy" == "on" ]] && networksetup -setsecurewebproxystate "$eth_service" on || networksetup -setsecurewebproxystate "$eth_service" off
    [[ "$socks_proxy" == "on" ]] && networksetup -setsocksfirewallproxystate "$eth_service" on || networksetup -setsocksfirewallproxystate "$eth_service" off
    [[ "$auto_proxy" == "on" ]] && networksetup -setautoproxystate "$eth_service" on || networksetup -setautoproxystate "$eth_service" off

    # Cleanup
    rm -rf "$STATE_DIR"
    echo "=== restore complete ==="
}

# === Subcommand: status ===
cmd_status() {
    echo "=== status ==="
    echo "state_dir: $STATE_DIR"
    echo "backup_exists: $([[ -f "$BACKUP_FILE" ]] && echo yes || echo no)"

    local wifi_if
    wifi_if="$(identify_wifi)"
    echo "wifi_interface: $wifi_if"

    local default_if
    default_if="$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')"
    echo "default_route_interface: $default_if"

    local eth_info
    if eth_info="$(discover_ax88179b 2>/dev/null)"; then
        local eth_service
        eth_service="$(echo "$eth_info" | jq -r .service)"
        echo "ax88179b_service: $eth_service"
        echo "ax88179b_info:"
        networksetup -getinfo "$eth_service" 2>/dev/null || echo "  (unable to get info)"
    else
        echo "ax88179b: NOT FOUND"
    fi
    echo "=== end status ==="
}

# === Main Dispatch ===
usage() {
    echo "Usage: $0 {prepare|check|restore|status}"
    echo ""
    echo "One-shot direct ethernet session manager for AX88179B adapter."
    echo "No background processes, no Wi-Fi mutations, no persistent daemons."
    exit 1
}

[[ $# -lt 1 ]] && usage

case "$1" in
    prepare) cmd_prepare ;;
    check)   cmd_check ;;
    restore) cmd_restore ;;
    status)  cmd_status ;;
    *)       usage ;;
esac
