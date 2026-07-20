# V1 Physical Keyboard Path Evidence

This is a public-safe, append-only evidence receipt. It records only observed
behavior and intentionally excludes device identifiers, serials, addresses,
private paths, screenshots, and account data.

```yaml
receipt_scope: V1_R7_BLE_TRANSPORT_STABILITY
responsive_ui:
  launch_canvas: PASS
  full_iPhone_safe_area: PASS
  fixed_legacy_letterbox: absent
  physical_device: true
firmware:
  pod_frame_queue: PASS
  clean_build: PASS
  upload: PASS
  reset_reason_log: implemented
observed_run:
  open_ack: PASS
  applied_ack_count: 8
  disconnect_after_text: absent_in_observed_log
  transport_stability_after_text: PASS
  firmware_reset_observed: false
full_v1_acceptance:
  status: PENDING
  remaining: backspace_ctrl_c_stop_resume_duplicate_suppression_reconnect_stability
private_identifiers_recorded: false
```

The observed iPhone log showed `OPENED`, followed by eight successful
`APPLIED` acknowledgements without a transport error or disconnect. This proves
the repaired short-operation transport path, not the complete V1 acceptance
matrix.
