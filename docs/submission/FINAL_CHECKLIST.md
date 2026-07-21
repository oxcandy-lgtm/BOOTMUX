# Build Week Final Checklist

```yaml
working_demo:
  companion_pty_websocket: GREEN
  standalone_judge_replay: GREEN
  live_local_judge_mode: GREEN
  iphone_terminal: IMPLEMENTED_PHYSICAL_BOOTMUX_READY_OBSERVED
  physical_ble_usb_hid: BOUNDED_PHYSICAL_ASCII_PATH_OBSERVED
  codex_bootmux_ready: CLEAN_VM_AND_PHYSICAL_RETURN_OBSERVED
  hid_mirror: CODE_GREEN_PHYSICAL_CONFIRMATION_PENDING

required_tool_evidence:
  codex:
    primary_thread: CONFIRMED
    majority_core_work: COMPLETE
    feedback_receipt: CAPTURED_PRIVATELY_AND_ENTERED_IN_DEVPOST
    readme_explanation: GREEN
    demo_narration: FINAL_MASTER_COMPLETE_OWNER_REPORTED
  gpt_5_6:
    meaningful_contribution: GREEN_PUBLIC_EVIDENCE_MAPPING
    architecture_evidence: GREEN
    verification_evidence: GREEN
    readme_explanation: GREEN
    demo_narration: FINAL_MASTER_COMPLETE_OWNER_REPORTED
  human_decision_boundary: GREEN_DOCUMENTED

submission:
  submitter_type: INDIVIDUAL
  country: JAPAN
  category: DEVELOPER_TOOLS
  license: MIT_GREEN
  readme: GREEN
  installation_instructions: GREEN
  supported_platforms: GREEN
  no_rebuild_judge_path: GREEN
  devpost_fields: PREPARED
  video_master: COMPLETE_OWNER_REPORTED
  video_public_upload: PENDING_CONFIRMATION
  final_devpost_link_review: PENDING
  terms_acceptance: PENDING
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

## Remaining submission-critical actions

1. Upload the completed final master to YouTube as **Public**.
2. Confirm the final video is under three minutes.
3. Play it from beginning to end and verify that the voiceover clearly explains:
   - what BOOTMUX does;
   - how Codex was used;
   - how GPT-5.6 was used.
4. Check audio balance, subtitles, redactions, and private information.
5. Open the YouTube URL in a signed-out or private browser window.
6. Enter the final YouTube URL in Devpost.
7. Re-open every repository, Judge Mode, and project link from the form.
8. Accept the Official Rules and Devpost Terms of Service.
9. Select **Submit project**.
10. Confirm the project no longer appears as a Devpost draft and save a completion screenshot.

## Non-blocking technical follow-up

The following improve the product but are not required to represent the current bounded Build Week demo honestly:

- physical selectable-copy acceptance;
- visible CLEAR acceptance;
- physical HID Mirror acceptance;
- repeatability receipts;
- Unicode HID;
- mouse support;
- continued post-bootstrap operation;
- broader packaging and platform validation.

None of these may be marked complete from Judge Replay, unit tests, or an edited reconstruction alone.
