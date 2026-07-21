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
    demo_narration: COMPLETE_OWNER_CONFIRMED
  gpt_5_6:
    meaningful_contribution: GREEN_PUBLIC_EVIDENCE_MAPPING
    architecture_evidence: GREEN
    verification_evidence: GREEN
    readme_explanation: GREEN
    demo_narration: COMPLETE_OWNER_CONFIRMED
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
  devpost_fields: SUBMITTED
  video_master: COMPLETE_OWNER_CONFIRMED
  video_public_upload: GREEN_OWNER_CONFIRMED
  video_url: https://www.youtube.com/watch?v=BNWTRxrVM6M
  repository_url_points_to_main: GREEN_OWNER_CONFIRMED
  final_devpost_link_review: GREEN_OWNER_CONFIRMED
  terms_acceptance: GREEN_OWNER_CONFIRMED_BY_SUCCESSFUL_SUBMISSION
  final_submission: GREEN_OWNER_CONFIRMED

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

## Submission-critical actions

All organizer-facing submission-critical actions are complete by owner confirmation:

1. the narrated demo was uploaded publicly to YouTube;
2. the final video URL was entered in Devpost;
3. the public repository URL points to `main`;
4. the private `/feedback` Session ID was entered;
5. the rules and terms were accepted as part of successful submission;
6. **Submit project** was completed before the deadline.

Public demo video: https://www.youtube.com/watch?v=BNWTRxrVM6M

## Non-blocking technical follow-up

The following improve the product but were not required to represent the bounded Build Week demo honestly:

- physical selectable-copy acceptance;
- visible CLEAR acceptance;
- physical HID Mirror acceptance;
- repeatability receipts;
- Unicode HID;
- mouse support;
- continued post-bootstrap operation;
- broader packaging and platform validation.

None of these may be marked complete from Judge Replay, unit tests, or an edited reconstruction alone.
