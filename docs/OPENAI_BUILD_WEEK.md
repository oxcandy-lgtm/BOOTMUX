# OpenAI Build Week Requirements for BOOTMUX

## Verification status

```yaml
verified_at: 2026-07-19 JST
competition: OpenAI Build Week
recommended_track: Developer Tools
source_priority:
  1: Official Rules
  2: Hackathon website and official updates
  3: Official FAQ and Resources
  4: Optional plugin output and community discussion
```

This page is a source-backed operational summary for BOOTMUX. It is not a substitute for the Official Rules. When sources conflict, the [Official Rules](https://openai.devpost.com/rules) control.

## Critical dates

| Event | Official Pacific time | Japan time |
|---|---|---|
| Registration closes | July 21, 2026 at 5:00 PM PDT | July 22, 2026 at 9:00 AM JST |
| Submission closes | July 21, 2026 at 5:00 PM PDT | July 22, 2026 at 9:00 AM JST |
| Winners announced | On or around August 12, 2026 at 2:00 PM PT | On or around August 13, 2026 at 6:00 AM JST |

The Official Rules list the judging period as July 22 through August 5. A separate schedule page has displayed a different judging end date. BOOTMUX therefore treats the Official Rules as authoritative and does not depend on the judging end date for any submission action.

Sources:

- [Official Rules — dates and timing](https://openai.devpost.com/rules)
- [Devpost schedule page](https://openai.devpost.com/details/dates)

## BOOTMUX category

BOOTMUX should enter the **Developer Tools** track because its primary user and use case are developers bootstrapping Codex and terminal access on a target computer.

The official track description includes developer testing, DevOps, agentic workflows, and security. A submission may enter only one track.

Sources:

- [Official Rules — Project Requirements and tracks](https://openai.devpost.com/rules)
- [Official FAQ — category selection](https://openai.devpost.com/details/faqs)

## Mandatory technology use

### Codex

Codex usage is mandatory. It must be demonstrated in:

- the Devpost text description;
- the public demo video with audio;
- the repository README;
- the `/feedback` Codex Session ID from the primary build thread.

Accepted Codex surfaces include the ChatGPT app, Codex CLI, an IDE extension, or the SDK. The official FAQ recommends Codex inside the ChatGPT desktop app but does not require that specific surface.

### GPT-5.6

GPT-5.6 usage is mandatory and must be meaningful rather than incidental or decorative. It does not need to be used for every task, but its contribution must be visible in the repository and explained in the demo video.

The rules do not explicitly require the BOOTMUX runtime to call the OpenAI API. BOOTMUX must nevertheless preserve clear evidence that GPT-5.6 contributed materially to the submitted project.

Sources:

- [Official FAQ — required Codex and GPT-5.6 use](https://openai.devpost.com/details/faqs)
- [Official Rules — project must be built with Codex and GPT-5.6](https://openai.devpost.com/rules)

## Primary Codex thread and `/feedback`

BOOTMUX must designate one Codex thread as the **Primary Build Thread**.

That thread should contain the majority of core implementation work for:

```text
V0 software terminal loop
→ V1 physical keyboard path
→ V2 terminal return
→ V3 Codex installation
→ V4 Codex connectivity and copy
```

When the majority of core functionality has been built, run:

```text
/feedback
```

Codex returns a Session ID for that thread. Copy the ID into the Devpost submission form.

Rules:

- use the main implementation thread, not a planning-only, test, or side thread;
- if work spans several threads, select the most representative thread;
- document the other meaningful Codex contributions in the README;
- do not commit the real Session ID to the public repository by default;
- store it in the private submission register and verify it before final submission.

Source:

- [Official FAQ — `/feedback` Session ID](https://openai.devpost.com/details/faqs)

## Existing-project boundary

Projects created before the Submission Period are allowed, but only work added during the Submission Period is evaluated.

BOOTMUX must distinguish:

```yaml
pre_existing:
  - initial concept
  - exploratory architecture
  - pre-period materials, if any

build_week_work:
  - V0 through V4 implementation
  - firmware and application code created during the period
  - Companion implementation
  - Codex installation and test flow
  - demo, judge test path, and submission material
```

Evidence should include dated commits, timestamped Codex sessions, or equivalent records showing that Codex and GPT-5.6 were used during the Submission Period.

Source:

- [Official Rules — New & Existing Projects](https://openai.devpost.com/rules)

## Required submission package

A complete submission requires:

1. a working project built with Codex and GPT-5.6;
2. one selected track;
3. a text description of the project and its operation;
4. a public YouTube demo video;
5. a code repository URL;
6. a README with setup, test, and tool-usage evidence;
7. the `/feedback` Session ID from the primary build thread.

For a Developer Tool, also include:

- installation instructions;
- supported platforms;
- a way for judges to test without rebuilding from source.

Source:

- [Official FAQ — submission requirements](https://openai.devpost.com/details/faqs)
- [Official Rules — Submission Requirements](https://openai.devpost.com/rules)

## Repository and licensing requirements

The repository must be either:

- public with relevant licensing; or
- private and shared with `testing@devpost.com` and `build-week-event@openai.com`.

For the public BOOTMUX route, selecting and committing an appropriate license is a submission blocker. The repository currently must not be submitted while it still states that no license has been selected.

The README must explain:

- setup instructions;
- supported platforms;
- how to test the project;
- required sample data, when applicable;
- how Codex accelerated development;
- where human product, engineering, and design decisions were made;
- how GPT-5.6 and Codex contributed;
- which work existed before Build Week and which work was added during it.

Open-source components are allowed when their licenses are followed and pre-existing or third-party work is disclosed.

Sources:

- [Official Rules — repository, README, licensing, and open source](https://openai.devpost.com/rules)
- [Official FAQ — README expectations](https://openai.devpost.com/details/faqs)

## Demo video requirements

The demo video must:

- be three minutes or less;
- be uploaded as a public YouTube video;
- clearly demonstrate a working project;
- include voice narration;
- explain what was built;
- explain how Codex was used;
- explain how GPT-5.6 was used;
- avoid unlicensed music, trademarks, or other copyrighted material.

The video may use AI-assisted narration. It must be in English or be accompanied by an English translation.

BOOTMUX should show, in one continuous or honestly edited narrative:

```text
clean target state
→ iPhone BLE input
→ ESP32-S3 USB HID entry
→ Codex installation or presence verification
→ one-shot Codex execution
→ terminal output returned to iPhone
→ native copy and paste of BOOTMUX_READY
```

Sources:

- [Official Rules — demo video and language requirements](https://openai.devpost.com/rules)
- [Official FAQ — demo video details](https://openai.devpost.com/details/faqs)

## Judge-accessible test path

Judges are not required to build or test the project. If they test it, they may use the supplied demo, test build, sandbox, or test account.

Because BOOTMUX uses an ESP32-S3 hardware bridge, the submission must not assume that judges own the same hardware. The project should provide both:

```text
Real Hardware Proof
  recorded iPhone → BLE → ESP32-S3 → USB HID demonstration

Judge Test Path
  prebuilt or easily launched software-only mode
  synthetic public-safe terminal fixture or replay
  copyable BOOTMUX_READY proof
```

The judge path must be labeled honestly and must not be presented as proof of the physical HID route. The Sponsor may request access to unusual hardware.

Source:

- [Official Rules — Testing and hardware access](https://openai.devpost.com/rules)
- [Official FAQ — judges are not required to rebuild](https://openai.devpost.com/details/faqs)

## Required and optional tools

| Tool or account | Status | BOOTMUX use |
|---|---|---|
| Devpost account and Build Week registration | Required | registration and submission |
| OpenAI account | Required | Codex and GPT-5.6 access |
| Codex | Required | primary implementation workflow and Session ID |
| GPT-5.6 | Required | meaningful project contribution |
| Git repository | Required | code, README, setup, evidence |
| Relevant repository license or private judge sharing | Required | repository eligibility |
| YouTube account | Required | public demo video |
| Physical iPhone | BOOTMUX V1 requirement | native input and copy proof |
| ESP32-S3 | BOOTMUX V1 requirement | BLE-to-USB HID bridge |
| Apple Silicon Mac and ARM64 Linux VM | BOOTMUX development plan | single-machine development and clean target reset |
| Devpost Hackathons Plugin | Optional | rules, resources, preparation, and submission assistance |
| OpenAI Discord and office hours | Optional | support and announcements |

## Devpost Hackathons Plugin

The plugin is optional and does not affect eligibility or judging. It is a helper, not the source of truth. The Official Rules and hackathon website always override plugin output.

Officially documented commands include:

```text
$find-hackathons
$start-hackathon
$resources
$prepare-submission
$submit
```

Recommended BOOTMUX use:

```text
$start-hackathon
  confirm registration and rules

$resources
  locate current official resources

$prepare-submission
  run the final security and eligibility audit

$submit
  assist with Devpost form completion
```

Do not treat a plugin checklist or planning conversation as proof that the project was built with Codex.

Sources:

- [Official Rules — optional plugin and source-of-truth warning](https://openai.devpost.com/rules)
- [Official FAQ — plugin commands](https://openai.devpost.com/details/faqs)

## Credits and API assumptions

The Resources page currently states that all available event credits have been distributed. BOOTMUX must proceed using the available plan or free tier and must not make completion depend on receiving additional promotional credits.

The event distributes Codex credits, not separate OpenAI API credits. Any API usage must use separately available billing or credits. API integration is optional unless BOOTMUX deliberately chooses it as part of the product.

Sources:

- [Official Resources — current credit availability](https://openai.devpost.com/resources)
- [Official FAQ — Codex credits and API credits](https://openai.devpost.com/details/faqs)

## Judging criteria

Projects that pass the initial eligibility and theme check are evaluated on equally weighted criteria:

1. Technological Implementation;
2. Design;
3. Potential Impact;
4. Quality of the Idea.

For BOOTMUX:

- **Technological Implementation:** prove the real BLE and USB HID path, Codex workflow, and working integration;
- **Design:** make the one-screen V1 coherent and reliable rather than exposing unfinished subsystems;
- **Potential Impact:** explain the target user who needs to bootstrap AI access on an unprepared machine;
- **Quality of the Idea:** show why a physical first path differs from ordinary remote terminals and agent frontends.

Source:

- [Official Rules — judging criteria](https://openai.devpost.com/rules)

## Current BOOTMUX submission blockers

```yaml
blockers:
  - V0 through V4 are not yet implemented and evidenced
  - primary Codex build thread must be designated
  - meaningful GPT-5.6 contribution must be recorded
  - public repository license must be selected
  - README Build Week scope and Codex/GPT-5.6 sections must be completed
  - judge-accessible no-rebuild test path must be created
  - feedback Session ID must be captured privately
  - public three-minute voice-narrated YouTube demo must be produced
  - Devpost fields must be completed before the deadline
```

## Source index

Authoritative and official pages checked for this document:

- [OpenAI Build Week Official Rules](https://openai.devpost.com/rules)
- [OpenAI Build Week FAQ](https://openai.devpost.com/details/faqs)
- [OpenAI Build Week Resources](https://openai.devpost.com/resources)
- [OpenAI Build Week Overview](https://openai.devpost.com/)
- [OpenAI Build Week Schedule](https://openai.devpost.com/details/dates)
- [OpenAI Build Week submission and plugin update](https://openai.devpost.com/updates/45282-openai-build-week-submissions-are-open-plugin-launch)
- [OpenAI supported countries and territories](https://platform.openai.com/docs/supported-countries)

## Change-control rule

This document is time-sensitive. Before final submission:

1. reopen the Official Rules;
2. reopen the FAQ and Resources pages;
3. compare deadlines and submission fields;
4. update this document when any requirement changed;
5. record the final verification date in the private submission register.
