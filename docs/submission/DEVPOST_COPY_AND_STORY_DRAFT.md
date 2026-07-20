# Devpost Copy and Story Draft

Status: working draft for OpenAI Build Week submission. This file is not the final submission copy.

This document contains public-safe copy only. Do not add the real `/feedback` Session ID, account information, private paths, hostnames, device serial numbers, or unpublished credentials.

## Project summary — maximum 200 characters

Character count: 191, including spaces and punctuation.

> Codex built BOOTMUX, a physical first mile for Codex: iPhone text crosses BLE and ESP32-S3 USB HID, while independently observed terminal output returns to the phone—architected with GPT-5.6.

## Core positioning

> **The physical first mile for Codex. Built by Codex. Architected and hardened with GPT-5.6.**

BOOTMUX is not another remote-terminal frontend. It addresses the moment before the normal developer path is ready: bare-metal setup, recovery, a clean VM, a headless machine, or a broken SSH route.

```text
physical input:
iPhone → BLE → ESP32-S3 → USB HID → target

independently observed return:
target PTY / Codex output → BOOTMUX Companion → WebSocket → iPhone
```

Codex built the major software, firmware, VM, testing, and repair layers. GPT-5.6 designed the asymmetric architecture, bounded contracts, adversarial reviews, and evidence boundaries. The human owner selected the problem and product direction, performed the physical setup and acceptance, and owns the final claims.

The central Build Week story is:

> Codex helped build the path that extends Codex itself into a computer before the normal AI workflow is ready.

## Story draft — original Japanese source

動機は実に単純でしたが、私に有り余るほどのエネルギーを与えてくれました。サーバーPCの初期セットアップです。

私の生活の中には、もう毎日必ずと言っていいほどAIが存在し、共存しています。しかしどうでしょう。サーバーPCをセットアップしている時、私が彼らと疎通する手段は、汚いディスプレイを拭いながらピントを合わせ、ChatGPTが一番読みやすい画角で、なんて考えながらターミナル画面を直撮りすることしかありませんでした。

例えるなら、車に乗っていたら、いきなり高速道路の中央分離帯で捨てられ、放置されたかのような絶望感を味わいました。他の運転手からはジロジロ見られます。それなら中央分離帯を走って目的地まで行け、と言うは易しですが、はっきり言って私はベイビーなのです。

ターミナルに文字を打てることすら奇跡の状態で、あなたは高速道路を四つん這いで渡り切れますか？という話なのです。

はっきり言いますが、人類に今一番必要なツールです。OSにネイティブAIが搭載されるか、このBOOTMUXを使うかの二択です。そしてこの問いは非常に簡単で、あなたならすぐ解けるはずです。AIを使わずともね。

## Final English story requirements

The final English version should preserve the personal voice and highway-median metaphor while accurately covering:

- the real server-PC setup and recovery problem;
- why photographing a dirty terminal display breaks the normal AI workflow;
- why BOOTMUX differs from SSH and ordinary remote terminals;
- the demonstrated iPhone, BLE, ESP32-S3 USB HID, VM, Companion, Codex, and terminal-return path;
- how Codex implemented the major project layers;
- how GPT-5.6 materially designed and hardened the architecture;
- the human product and physical-acceptance decisions;
- the distinction between observed capabilities and future roadmap claims.

## Current publishable claims

```yaml
publishable:
  - Codex built the major Go, SwiftUI, firmware, VM, testing, and repair layers
  - GPT-5.6 materially contributed to architecture, contracts, review, and claim safety
  - bounded physical ASCII BLE and USB HID input was owner-observed
  - Codex was installed and invoked in a clean ARM64 VM
  - BOOTMUX_READY returned through the Companion to the physical iPhone
  - Judge Mode is available without rebuilding

pending:
  - selectable copy and exact paste owner confirmation
  - visible CLEAR owner confirmation
  - physical HID Mirror confirmation
  - repeatability receipt

not_claimed:
  - Unicode HID
  - mouse support
  - fully offline target operation
  - full terminal emulation
  - production readiness
```
