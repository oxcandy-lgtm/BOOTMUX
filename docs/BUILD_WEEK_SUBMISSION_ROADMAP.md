# BOOTMUX Build Week Submission Roadmap

## Purpose

This roadmap makes OpenAI Build Week compliance a first-class delivery path rather than an end-of-project checklist.

The technical path and submission path run together:

```text
V0 → V1 → V2 → V3 → V4
              │
              └──────────────┐
                             ↓
BW0 → BW1 → BW2 → BW3 → BW4 → BW5 → BW6 → BW7 → BW8 → BW9
```

A working V4 without the Build Week evidence package is not a complete hackathon delivery.

Official requirements and sources are documented in [OpenAI Build Week Requirements](OPENAI_BUILD_WEEK.md).

## Status vocabulary

```text
OPEN
IN_PROGRESS
BLOCKED
GREEN
```

A gate becomes `GREEN` only when its required evidence exists.

---

# BW0 — Registration, source snapshot, and category

## Goal

Establish eligibility and freeze the official requirements used by the project.

## Required actions

- join OpenAI Build Week through Devpost;
- confirm the entrant is represented correctly;
- select `Developer Tools` as the intended track;
- save the official deadline in both Pacific Time and JST;
- record the verification date for the Official Rules, FAQ, and Resources pages;
- note that the optional plugin is not the source of truth.

## Acceptance gate

```yaml
registration_confirmed: true
track: Developer Tools
official_deadline_jst: 2026-07-22T09:00:00+09:00
official_rules_checked: true
faq_checked: true
resources_checked: true
```

## Stop rule

Do not wait until submission day to discover that registration or the selected category is missing.

---

# BW1 — Primary Codex thread and GPT-5.6 evidence

## Goal

Create one auditable development spine that satisfies the mandatory tool-use requirements.

## Required actions

- designate one Codex thread as `Primary Build Thread`;
- use that thread for the majority of V0–V4 core implementation;
- use GPT-5.6 meaningfully for at least one core implementation, debugging, architecture, or verification task;
- preserve dated commits and session timestamps;
- maintain a short private log of the important Codex and GPT-5.6 contributions;
- keep side threads subordinate and document their contribution when significant.

## Acceptance gate

- the primary thread contains real implementation work, not only planning;
- the majority of core functionality is attributable to that thread;
- at least one meaningful GPT-5.6 contribution can be explained specifically;
- README wording can distinguish Codex acceleration from human decisions;
- no required evidence depends on memory alone.

## Failure conditions

- the selected thread is a test or planning-only conversation;
- core implementation is scattered across many undocumented threads;
- GPT-5.6 appears only in a name, screenshot, or decorative prompt;
- the contribution cannot be connected to code, design, debugging, or verification.

---

# BW2 — Build Week scope ledger

## Goal

Separate pre-existing BOOTMUX work from work added during the Submission Period.

## Required actions

Create and maintain a scope ledger containing:

```yaml
pre_existing:
  - concept and exploratory design created before the Submission Period

submission_period:
  - implementation commits
  - firmware changes
  - iPhone application changes
  - Companion changes
  - Codex bootstrap and verification changes
  - judge test path
  - demo and submission assets
```

For every submission-period claim, preserve at least one of:

- dated commit;
- timestamped Codex session;
- versioned build artifact;
- public-safe evidence receipt;
- dated demo recording.

## Acceptance gate

- the README can state exactly what is new;
- every judged implementation feature has a dated source or artifact;
- pre-existing architecture is not presented as newly implemented;
- no private prompt transcript is published merely to prove timing.

---

# BW3 — Technical V1 completion

## Goal

Close V0 through V4 with repeatable evidence.

## Entry condition

BW0 through BW2 are active and the Primary Build Thread is being used.

## Required technical gates

```text
V0 software terminal loop
V1 physical keyboard path
V2 terminal return
V3 Codex installation
V4 Codex connectivity and native copy
```

## Acceptance gate

- a clean target state is restorable;
- iPhone text reaches the target through BLE and ESP32-S3 USB HID;
- target terminal output reaches the iPhone;
- Codex installation or clean-state presence verification is visible;
- a bounded Codex invocation returns `BOOTMUX_READY`;
- `BOOTMUX_READY` is selected, copied, and pasted on the iPhone;
- the run is repeatable;
- no hidden manual terminal bypasses the demonstrated input path.

## Build Week coupling

During implementation, record:

- Codex decisions and major iterations;
- GPT-5.6 contribution;
- commit identifiers;
- build identifiers;
- evidence suitable for the README and demo narration.

---

# BW4 — Judge-accessible test path

## Goal

Allow judges to understand or test BOOTMUX without rebuilding the full hardware stack.

## Required deliverables

### Real Hardware Proof

- recorded iPhone-to-BLE-to-ESP32-S3-to-USB-HID path;
- visible target reaction;
- terminal return and native copy proof.

### Judge Test Mode

- prebuilt or easily launched Companion test mode;
- public-safe synthetic terminal fixture or replay;
- clear instructions;
- no requirement for the judge to compile firmware or the phone app;
- visible statement that this mode does not prove the physical HID route.

## Acceptance gate

- installation instructions exist;
- supported platforms are explicit;
- test steps fit in a short sequence;
- no personal credentials are needed;
- test artifacts remain available free of charge through the judging period;
- a judge can see the core terminal-and-copy experience without owning the hardware.

## Stop rule

Do not call a source-only repository a complete Developer Tools testing path.

---

# BW5 — Repository, README, and license gate

## Goal

Make the repository eligible and judge-readable.

## Required actions

- select and commit an appropriate repository license for the public-submission route;
- include setup instructions;
- include supported platforms;
- include the judge test path;
- include sample-data or synthetic-fixture instructions when required;
- document the Build Week scope boundary;
- document how Codex accelerated development;
- document where human product, engineering, and design decisions were made;
- document how GPT-5.6 contributed;
- disclose third-party and pre-existing work;
- include a concise architecture and demo flow.

## Required README headings before submission

```text
Build Week Scope
Installation
Supported Platforms
Judge Test Mode
How to Run the Hardware Demo
How Codex Was Used
How GPT-5.6 Was Used
Human Decisions
Third-Party and Pre-Existing Work
Security and Privacy Notes
```

## Acceptance gate

- license file exists and matches the chosen public route;
- README instructions work from a clean environment or declared test artifact;
- all required headings contain specific, accurate content;
- no secret, personal identifier, or private infrastructure detail is present;
- the repository URL is ready for the Devpost form.

## Submission blocker

```text
No selected license
→ public repository route is RED
→ Devpost submission must not proceed
```

---

# BW6 — `/feedback` Session ID receipt

## Goal

Capture the required identifier from the correct Codex thread.

## Required actions

After the majority of core functionality has been built in the Primary Build Thread, run:

```text
/feedback
```

Then:

- copy the returned Session ID exactly;
- store it in the private submission register;
- label the associated thread and date;
- verify that this is the thread containing the majority of core work;
- prepare the ID for the Devpost form.

## Acceptance gate

```yaml
primary_thread_confirmed: true
feedback_command_run: true
session_id_captured_privately: true
session_id_ready_for_devpost: true
```

## Security rule

The actual Session ID is not committed to the public repository by default.

## Failure conditions

- ID came from a side thread;
- ID was copied incompletely;
- no one can identify which thread the ID represents;
- the ID exists only in an unverified screenshot;
- the submission form is opened without the ID available.

---

# BW7 — Three-minute narrated demo

## Goal

Produce the mandatory public YouTube demo while proving the strongest BOOTMUX story.

## Required structure

```text
0:00–0:20  Problem and user
0:20–0:40  BOOTMUX physical path
0:40–1:25  Real keyboard/bootstrap demonstration
1:25–2:05  Codex and GPT-5.6 contribution
2:05–2:35  BOOTMUX_READY returned to iPhone
2:35–2:50  Native copy and paste
2:50–3:00  Impact and closing claim
```

The exact edit may change, but the final video must remain three minutes or less.

## Required narration

The audio must specifically explain:

- what BOOTMUX does;
- how Codex was used to build it;
- how GPT-5.6 was used;
- what was demonstrated on real hardware;
- which path is a development or judge-test path.

## Acceptance gate

- public YouTube visibility is confirmed in a signed-out browser;
- runtime is three minutes or less;
- voice narration is audible;
- the project visibly works;
- Codex use is described specifically;
- GPT-5.6 use is described specifically;
- no account identifier, token, notification, hostname, or private path is visible;
- no unlicensed music or protected material is included;
- English narration or translation is present;
- the final URL is ready for Devpost.

## Stop rule

A silent screen recording or background-music-only video is RED.

---

# BW8 — Submission dry run and official re-verification

## Goal

Find compliance failures before the deadline.

## Required actions

- reopen the Official Rules;
- reopen the FAQ and Resources pages;
- confirm that deadlines and form fields have not changed;
- run the optional `$prepare-submission` helper when available;
- manually verify every result against official sources;
- open the Devpost submission form and fill a draft;
- test every public link in a signed-out browser;
- verify repository access and license;
- verify the video URL;
- verify the judge test path;
- verify the `/feedback` Session ID;
- run the publication-safety checklist;
- capture screenshots of completed fields without exposing the Session ID publicly.

## Acceptance gate

```yaml
rules_rechecked: true
all_links_publicly_accessible: true
repository_gate: GREEN
license_gate: GREEN
judge_test_gate: GREEN
feedback_gate: GREEN
video_gate: GREEN
security_gate: GREEN
devpost_draft_complete: true
```

## Source-of-truth rule

Optional plugin output is advisory. Any disagreement with the Official Rules is resolved in favor of the Official Rules.

---

# BW9 — Final submission and lock

## Goal

Submit early enough to recover from account, upload, or form failures.

## Internal timing rule

Freeze implementation and submit the first complete version at least six hours before the official deadline whenever possible.

Official deadline:

```text
2026-07-21 17:00 PDT
2026-07-22 09:00 JST
```

## Final required fields

- `Developer Tools` track;
- project title and text description;
- repository URL;
- public YouTube URL;
- judge test instructions;
- supported platforms;
- `/feedback` Session ID;
- Codex usage explanation;
- GPT-5.6 usage explanation;
- team or representative information.

## Acceptance gate

- Devpost confirms the submission;
- the submitted version is visible in the entrant dashboard;
- a private submission receipt or screenshot is saved;
- every submitted link still works;
- no post-deadline edit is required for correctness;
- the project and judge test artifacts remain available through judging.

## Final lock rule

After the Submission Period ends, treat the submission as immutable except for changes explicitly permitted by the Sponsor or Devpost.

---

# Critical execution order

```text
NOW
├─ BW0 registration and rules
├─ BW1 primary thread
└─ BW2 scope ledger

BUILD
├─ V0–V4
└─ BW3 evidence capture

PACKAGE
├─ BW4 judge path
├─ BW5 README and license
└─ BW6 feedback receipt

PRESENT
├─ BW7 video
├─ BW8 dry run
└─ BW9 submit
```

The V0–V4 work and BW0–BW9 work must not be treated as separate last-minute projects.

# Public versus private artifacts

## Public repository

- source code;
- license;
- setup and test documentation;
- Build Week scope;
- Codex and GPT-5.6 contribution summary;
- synthetic fixtures;
- public-safe demo evidence.

## Private submission register

- actual `/feedback` Session ID;
- Devpost account and submission status;
- unpublished video drafts;
- signed-out link-check results;
- sensitive authentication notes;
- private submission confirmation screenshots.

# Final scheduling rule

Until submission is confirmed, every task must answer one of these questions:

```text
Does it close V0–V4?
Does it close BW0–BW9?
Does it remove a submission blocker?
```

If the answer is no, defer it until after Build Week submission.
