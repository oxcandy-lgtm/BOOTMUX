# V2–V6 Codex Physical Return Progress

This is an append-only, public-safe progress receipt for the integrated ARM64 VM and iPhone return path. It excludes IP addresses, hostnames, credentials, authentication URLs, device identifiers, serials, and private paths.

    task_id: BOOTMUX-V2-V6-R2-CODEX-PHYSICAL-RETURN-CLOSEOUT
    validation_host: MACBOOK_AIR_M1
    latest_implementation_head: 1098e6fa7bc5eb84a99be50b8f3c08a0642a9c32
    scope: integrated_vm_codex_probe_and_physical_iphone_return_preparation

## Verified

    lima:
      provider: Lima
      version: 2.1.4
      arm64_demo_vm: PASS
      clean_vm_recreate: PASS
      demo_vm_clone: PASS
      guest_network_dns_tls_egress: PASS
    codex:
      official_cli_install: PASS
      version: codex-cli_0.144.6
      human_authentication: PASS
      direct_vm_prompt: PASS
      direct_vm_marker: BOOTMUX_READY
    companion:
      gofmt: PASS
      go_test: PASS
      go_test_race: PASS
      go_vet: PASS
      normal_build: PASS
      probe_build: PASS
      live_judge_probe: PASS
      host_forwarder_judge_probe: PASS
      codex_prompt_marker: BOOTMUX_READY
    iphone_client:
      swift_syntax_parse: PASS
      simulator_build: PASS
      local_ip_ats_exception: IMPLEMENTED
      terminal_controls: CONNECT_DISCONNECT_CLEAR_SEPARATED
      clear_invalidation: IMPLEMENTED

The direct Codex probe and the production Companion codex_prompt path both returned the exact BOOTMUX_READY marker. The Companion path used the real Codex executable installed inside the demo VM; no fixture or fake Codex process was used for this receipt.

The iOS app received a narrow ATS repair for private local IP/CIDR ranges, because iOS 17+ rejects cleartext WebSocket connections to IP addresses unless the IP/CIDR exception is declared. The app retains NSAllowsLocalNetworking and does not enable global arbitrary loads. The Settings sheet now places CONNECT, DISCONNECT, CLEAR, and SEND on separate rows and displays TERM state. CLEAR cancels pending publication and sets an explicit status message.

## Physical return status

    physical_iphone_codex_return: NOT_PROVEN
    physical_marker_observed: false
    physical_copy_observed: false
    mac_lan_interface_detection: PASS
    iphone_to_mac_forwarder_reachability: NOT_PROVEN
    term_error_observed_on_device: true
    ats_error_observed_before_latest_reinstall: true

The device-side TERM ERROR occurred before physical return was proven. The reported ATS policy message is consistent with the pre-repair app binary. Reporter disconnected and RTIInputSystemClient messages are diagnostic logs associated with the failed connection/input lifecycle, not evidence that the VM Codex probe failed. The latest app binary must be installed before repeating the physical test.

The physical endpoint must use the Mac's currently active LAN IPv4 address, not a hardcoded repository value and not 127.0.0.1. The Mac and iPhone must be on the same reachable network, BOOTMUX must have Local Network permission, and the host forwarder must be running on its bounded demo port. The actual address is intentionally omitted from this public receipt.

## Local commands and results

    limactl list                                                PASS — ARM64 demo VM available
    codex login status                                          PASS — authenticated
    codex exec -s read-only ...                                 PASS — BOOTMUX_READY
    go test ./...                                               PASS
    go test -race ./...                                         PASS
    go vet ./...                                                PASS
    go build ./...                                              PASS
    go build -tags probe .                                      PASS
    curl http://<local-address>:<forward-port>/judge             PASS — live Judge HTML
    swiftc -parse iphone/BOOTMUX/*.swift iphone/BOOTMUXTests/*.swift PASS
    xcodebuild ... CODE_SIGNING_ALLOWED=NO build               PASS
    plutil -lint iphone/BOOTMUX/Info.plist                      PASS
    git diff --check                                            PASS

No GitHub Actions were used, inspected, triggered, or depended upon. GitHub Issues were not accessed, searched, created, edited, commented on, or used through an API. PR #1 remains Draft, open, and unmerged. The existing local Xcode signing-settings change remains uncommitted and is excluded from this receipt.

## Classification

    classification: YELLOW_V2_V6_VM_CODEX_GREEN_PHYSICAL_IPHONE_RETURN_PENDING
    next_owner_action: install_latest_app_and_repeat_local_endpoint_probe
