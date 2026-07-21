# Archived Devpost Copy and Story Source

Status: historical source material. This file is **not** the canonical submission copy.

Use these current sources instead:

- [Canonical Project Story](../PROJECT_STORY.md)
- [Devpost Submission Map](DEVPOST_FINAL_DRAFT.md)
- [Claim and Evidence Matrix](CLAIM_EVIDENCE_MATRIX.md)

This document is retained because it contains the builder's original Japanese motivation and the early public-safe positioning from which the canonical English story was developed. Do not add the real `/feedback` Session ID, account information, private paths, hostnames, device serial numbers, endpoints, or credentials.

## Early project summary

> Codex built BOOTMUX, a physical first mile for Codex: iPhone text crosses BLE and ESP32-S3 USB HID, while independently observed terminal output returns to the phone—architected with GPT-5.6.

## Core positioning

> **The physical first mile for Codex. Built by Codex. Architected and hardened with GPT-5.6.**

BOOTMUX is not another remote-terminal frontend. It addresses the moment before the normal developer path is ready: initial setup, recovery, a clean VM, a headless machine, or a broken SSH route.

```text
physical input:
iPhone → BLE → ESP32-S3 → native USB HID → target

independently observed return:
target PTY / Codex output → BOOTMUX Companion → local WebSocket → iPhone
```

Codex built the major software, firmware, VM, testing, and repair layers. GPT-5.6 designed the asymmetric architecture, bounded contracts, adversarial reviews, and evidence boundaries. The human owner selected the problem and product direction, performed physical setup and observation, edited the final video, and owns every final claim.

## Original Japanese motivation

動機は実に単純でしたが、私に有り余るほどのエネルギーを与えてくれました。サーバーPCの初期セットアップです。

私の生活の中には、もう毎日必ずと言っていいほどAIが存在し、共存しています。しかしどうでしょう。サーバーPCをセットアップしている時、私が彼らと疎通する手段は、汚いディスプレイを拭いながらピントを合わせ、ChatGPTが一番読みやすい画角で、なんて考えながらターミナル画面を直撮りすることしかありませんでした。

例えるなら、車に乗っていたら、いきなり高速道路の中央分離帯で捨てられ、放置されたかのような絶望感を味わいました。他の運転手からはジロジロ見られます。それなら中央分離帯を走って目的地まで行け、と言うは易しですが、はっきり言って私はベイビーなのです。

ターミナルに文字を打てることすら奇跡の状態で、あなたは高速道路を四つん這いで渡り切れますか？という話なのです。

はっきり言いますが、人類に今一番必要なツールです。OSにネイティブAIが搭載されるか、このBOOTMUXを使うかの二択です。そしてこの問いは非常に簡単で、あなたならすぐ解けるはずです。AIを使わずともね。

## Current public boundary

Publishable:

- Codex built the major Go, SwiftUI, firmware, VM, Judge Mode, testing, and repair layers;
- GPT-5.6 materially contributed to architecture, contracts, root-cause review, and claim safety;
- bounded physical ASCII BLE and native USB HID input was owner-observed;
- Codex was installed and invoked in a clean ARM64 VM;
- `BOOTMUX_READY` returned through the Companion to the physical iPhone;
- Judge Mode is available without rebuilding.

Still pending:

- physical selectable-copy and exact paste acceptance;
- visible CLEAR acceptance;
- physical HID Mirror acceptance;
- repeatability receipt.

Not claimed:

- Unicode HID;
- mouse support;
- fully offline target operation;
- full terminal emulation;
- continued post-bootstrap operation;
- production readiness.
