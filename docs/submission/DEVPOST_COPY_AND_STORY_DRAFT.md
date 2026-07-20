# Devpost Copy and Story Draft

Status: working draft for OpenAI Build Week submission. This file is not the final submission copy.

This document contains public-safe copy only. Do not add the real `/feedback` Session ID, account information, private paths, hostnames, device serial numbers, or unpublished credentials.

## Project summary — maximum 200 characters

Character count: 198, including spaces and punctuation.

> Conceived and architected by GPT-5.6, BOOTMUX turns an iPhone and ESP32-S3 into a wireless keyboard, mouse, and live terminal that can bootstrap and operate Codex—even when the target PC is offline.

## Story draft — original Japanese source

動機は実に単純でしたが、私に有り余るほどのエネルギーを与えてくれました。サーバーPCの初期セットアップです。

私の生活の中には、もう毎日必ずと言っていいほどAIが存在し、共存しています。しかしどうでしょう。サーバーPCをセットアップしている時、私が彼らと疎通する手段は、汚いディスプレイを拭いながらピントを合わせ、ChatGPTが一番読みやすい画角で、なんて考えながらターミナル画面を直撮りすることしかありませんでした。

例えるなら、車に乗っていたら、いきなり高速道路の中央分離帯で捨てられ、放置されたかのような絶望感を味わいました。他の運転手からはジロジロ見られます。それなら中央分離帯を走って目的地まで行け、と言うは易しですが、はっきり言って私はベイビーなのです。

ターミナルに文字を打てることすら奇跡の状態で、あなたは高速道路を四つん這いで渡り切れますか？という話なのです。

はっきり言いますが、人類に今一番必要なツールです。OSにネイティブAIが搭載されるか、このBOOTMUXを使うかの二択です。そしてこの問いは非常に簡単で、あなたならすぐ解けるはずです。AIを使わずともね。

## Final English story placeholders

The final English version should preserve the personal voice and highway-median metaphor while accurately covering:

- the real server-PC setup problem;
- why photographing a dirty terminal display breaks the normal AI workflow;
- how BOOTMUX keeps an iPhone, ESP32-S3, the target terminal, Codex, and GPT-5.6 connected;
- which architecture and implementation decisions were conceived or accelerated by GPT-5.6;
- the demonstrated BLE, USB HID, keyboard, mouse, terminal-return, offline-target, and post-boot capabilities;
- the distinction between implemented capabilities and future roadmap claims.

## Claim-safety notes before final submission

Do not convert the following into final claims until corresponding evidence exists:

- native USB HID enumeration on the real ESP32-S3 board;
- real iPhone-to-BLE-to-ESP32-S3 input;
- mouse support;
- offline-target communication;
- continued post-boot operation;
- Codex installation and `BOOTMUX_READY` proof;
- GPT-5.6 contribution connected to specific commits or implementation decisions.
