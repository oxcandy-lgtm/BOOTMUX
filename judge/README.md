# BOOTMUX Judge Mode

Judge Mode lets reviewers inspect the terminal, session, observed-output, selection, and copy experience without rebuilding the hardware stack.

## Fastest path — standalone offline replay

Requirements: any modern browser on macOS, Windows, or Linux.

1. Download or clone the repository.
2. Open `judge/index.html` directly in a browser.
3. Select **Replay BOOTMUX_READY**.
4. Select and copy the resulting terminal text using native browser behavior.
5. Use reset and simulated-command controls to inspect the bounded session experience.

This path requires no build, account, credential, network connection, private endpoint, executable, or physical hardware.

## Packaged macOS arm64 path

1. Open `dist/bootmux-judge-macos-arm64/`.
2. Run `START_JUDGE_MODE.command`.
3. If Gatekeeper blocks it, use right-click → **Open**.
4. Open `http://127.0.0.1:8765/judge` if the browser does not open automatically.
5. Press Ctrl-C in the launcher terminal when finished.

The package binds only to loopback.

## Live local Companion path

Requirements: Go and a Unix-like environment.

From the repository root:

```sh
cd companion
go test ./...
go run . -addr 127.0.0.1:8765
```

Open:

```text
http://127.0.0.1:8765/judge
```

Choose **Connect live Companion**. Live mode sends a synthetic command through `/v1/terminal` and renders only output observed from the target-side PTY.

## What this proves

Judge Mode demonstrates:

- the terminal presentation;
- session creation and reset behavior;
- independently observed PTY output in live mode;
- selectable text and native copy behavior;
- a no-build reviewer path.

## What this does not prove

Judge Mode is not evidence of:

- physical BLE transport;
- ESP32-S3 firmware execution;
- native USB HID delivery;
- a physical Codex return;
- physical iPhone copy/CLEAR acceptance;
- production readiness or repeatability.

Those claims are kept separate in the [Claim and Evidence Matrix](../docs/submission/CLAIM_EVIDENCE_MATRIX.md) and public evidence records.
