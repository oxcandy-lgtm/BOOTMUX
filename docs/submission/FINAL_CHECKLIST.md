# Build Week Final Checklist

```yaml
working_demo:
  companion_pty_websocket: GREEN
  standalone_judge_replay: GREEN
  live_local_judge_mode: GREEN
  iphone_terminal: PHYSICAL_BOOTMUX_READY_OBSERVED_COPY_PENDING
  physical_ble_usb_hid: BOUNDED_PHYSICAL_ASCII_PATH_OBSERVED
  codex_bootmux_ready: DIRECT_VM_COMPANION_AND_PHYSICAL_RETURN
  hid_mirror: CODE_GREEN_PHYSICAL_CONFIRMATION_PENDING

required_tool_evidence:
  codex:
    primary_thread: CONFIRMED
    majority_core_work: COMPLETE
    feedback_receipt: CAPTURED_PRIVATELY
    readme_explanation: GREEN
    demo_narration: FINAL_VIDEO_PENDING
  gpt_5_6:
    meaningful_contribution: GREEN_PUBLIC_EVIDENCE_MAPPING
    architecture_evidence: GREEN
    verification_evidence: GREEN
    readme_explanation: GREEN
    demo_narration: FINAL_VIDEO_PENDING
  human_decision_boundary: GREEN_DOCUMENTED

submission:
  track: DEVELOPER_TOOLS
  license: MIT_GREEN
  readme: GREEN
  installation_instructions: GREEN
  supported_platforms: GREEN
  no_rebuild_judge_path: GREEN
  devpost_draft: GREEN_WORKING_DRAFT
  demo_script: GREEN
  video: IN_PROGRESS_NOT_PUBLIC
  registration: HUMAN_CONFIRMATION_PENDING
  final_devpost_review: PENDING
  final_submission: NOT_CONFIRMED

privacy:
  session_id_in_repository: false
  private_endpoint_in_repository: false
  signing_material_in_repository: false
  device_identifiers_in_repository: false
  github_issues_used: false
  github_actions_used: false
  production_ready_claim: false

owner_acceptance:
  selectable_copy: PENDING_OWNER_CONFIRMATION
  clear_visible_feedback: PENDING_OWNER_CONFIRMATION
  physical_hid_mirror: PENDING_OWNER_CONFIRMATION
  repeatability: PENDING
```

Before submission, the owner must:

1. confirm Devpost registration and the Developer Tools track;
2. finish the narrated video under three minutes;
3. explicitly explain how Codex built the major implementation layers;
4. explicitly explain how GPT-5.6 designed and hardened the architecture;
5. complete privacy review and public YouTube upload;
6. verify public links in a signed-out browser;
7. enter the private `/feedback` Session ID into Devpost;
8. complete the final claim review and submit.

High-value physical acceptance remains COPY, CLEAR, HID Mirror, and repeatability. These improve the submission but must not be marked passed without observation.
