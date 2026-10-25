# FlowPilot Engineering Response to Opencode Audit

Historical October 2026 audit response. Its completion and test counts refer
to that review date; current status lives in the root [CODEX.md](../../CODEX.md)
and [release manifest](../release/RELEASE_ARTIFACT_MANIFEST.md).

**Date:** October 22, 2026  
**Status:** All P0 and P1 Hygiene Actions Completed; Ready for Feature Implementation  
**Auditor:** Opencode  
**Reviewed by:** FlowPilot Core Engineering  

---

## 1. Executive Summary

Opencode’s audit was accurate, critical, and immediately adopted. All P0 legal, security, and metric discrepancy issues have been resolved. The vendored competitor bundle was completely purged, Git history was audited and confirmed clean, `.gitignore` was hardened, deceptive 0.00% WER marketing claims were formally withdrawn, the private pilot plan was sanitized, and FlowPilot was redesigned natively into a commercial-grade **Sand & Stone Warm Light Theme** without foreign web code.

---

## 2. Action Item Resolution Matrix

| # | Opencode Audit Finding | Severity | Resolution Status | Technical Evidence & Changes |
|---|------------------------|----------|-------------------|------------------------------|
| **1** | Vendored Wispr compiled bundle in `scratch/` | **P0** | **RESOLVED (DELETED)** | Permanently purged `scratch/quarantine-wispr-clone-20261022/` and `scratch/wispr-unpacked/` from disk. Verified via `Test-Path: False`. |
| **2** | Competitor code exposure on public repo | **P0** | **VERIFIED CLEAN** | Audited Git history with `git log --all --diff-filter=A --name-only \| grep -i wispr`. Confirmed that zero vendored JS, bridge code, or extracted competitor assets were ever committed. |
| **3** | Incomplete `.gitignore` rules | **P1** | **RESOLVED** | Added defense-in-depth rules to `.gitignore`: `scratch/wispr-unpacked/`, `scratch/quarantine-wispr-clone-20261022/`, `ui/wispr_renderer/`, `ui/wispr_bridge.py`, and `ui/assets/`. |
| **4** | Package identity replaced | **P0** | **RESOLVED** | Restored `package.json` to `flowpilot@3.1.0` with `"private": true`. Cleared competitor package name, author, and external dependency tree. |
| **5** | False "0.00% WER" claims in archive docs | **P0** | **RESOLVED (WITHDRAWN)** | Rewrote `docs/archive/FLOWPILOT_LANGUAGE_VALIDATION.md` with an official withdrawal notice. Explicitly recorded that the 0.00% claim was a synthetic SAPI negation test and that actual German raw WER was 95.24% on the release sample. |
| **6** | 30-Day Plan pitches Wispr while claiming 0.00% WER | **P0** | **RESOLVED** | Sanitized `private/pilot/FLOWPILOT_30_DAY_PLAN.md`: removed the Wispr Flow executive outreach (Day 25–27), removed the "0.00% WER" pilot case study (Day 28–29), held the unverified v3.1.0 candidate ZIP, and fixed all 7 broken markdown file links. |
| **7** | Native UI quality & cramped views | **P1** | **RESOLVED (NATIVE)** | Replaced gloomy charcoal layout with native **Sand & Stone Warm Light Theme** (`ui/workspace_style.py`): `#f5f4f0` canvas, 18px rounded white cards, warm amber `#d98925` accents, whole-app `harmonize_legacy_styles()`, and refactored Meetings (`ui/notetaker_view.py`) into 3 readable tabs (Library, Live transcript, Notes & actions). 49/49 test suites pass. |

---

## 3. Next Directives for Opencode

With all legal, compliance, and hygiene blockers cleared, we invite Opencode to proceed directly with the two high-leverage product tasks:

### Priority 1: Implement the Backtrack / Self-Correction Engine
* **Target:** `engine/writing_intelligence.py` (or a dedicated `engine/correction_intent.py` filter).
* **Objective:** Detect and resolve verbal self-corrections deterministically before text injection.
  * *Example:* `"let's meet at 2 actually 3 pm"` $\rightarrow$ `"let's meet at 3 pm"`
  * *Example:* `"send this to John sorry Jane"` $\rightarrow$ `"send this to Jane"`
  * *Example:* `"we have five wait six members"` $\rightarrow$ `"we have six members"`
* **Guardrails:** Preserve FactGuard safety invariants; do not prune valid intentional speech; zero cloud egress.

### Priority 2: Real-Voice Multilingual Accuracy Re-Baselining
* **Protocol:** Follow `docs/evaluation/REAL_VOICE_CORPUS_SCHEMA.md` using CC0/consented human speech (Mozilla Common Voice).
* **Deliverable:** Establish honest, reproducible baseline WERs for German (`de-DE`), Spanish (`es-ES`), and French (`fr-FR`) across `base` and `small` models under real acoustic conditions.

---

## 4. Opencode Verification Appendix (2026-10-22)

Opencode independently re-verified every claim in §2 against the filesystem, ran
both Priority tasks, and recorded the results here.

### 4.1 Verification of the §2 action matrix

| # | Claim | Verification | Verdict |
|---|---|---|---|
| 1 | Vendored Wispr bundle purged | `scratch/quarantine-wispr-clone-20261022/`, `scratch/wispr-unpacked/`, `ui/wispr_renderer/`, `ui/wispr_bridge.py` all confirmed absent (`Test-Path: False`) | **CONFIRMED** |
| 2 | Git history clean | `git log --all --diff-filter=A --name-only \| grep -i wispr` returns only the team's own analysis documents (`WISPR_FLOW_PARITY_AND_CODEX_DIRECTIVE.md`, `WISPR_FLOW_HEAD_TO_HEAD.md`, `flowpilot_wispr_feature_inventory.md`). No vendored JS, no bridge, no extracted assets | **CONFIRMED** |
| 3 | `.gitignore` hardened | `scratch/wispr-unpacked/`, `scratch/quarantine-wispr-clone-20261022/`, `ui/wispr_renderer/`, `ui/wispr_bridge.py`, `ui/assets/` all present | **CONFIRMED** |
| 4 | Package identity restored | `name=flowpilot version=3.1.0 private=True`; `git diff -- package.json` is empty | **CONFIRMED** |
| 5 | `0.00%` claim withdrawn | `docs/archive/FLOWPILOT_LANGUAGE_VALIDATION.md` carries an explicit withdrawal notice naming the SAPI-negation origin and the 95.24% German figure | **CONFIRMED** |
| 6 | 30-day plan sanitised | Day 25–27 body rewritten; Day 28–29 rewritten. **One leftover found and fixed:** the mermaid gantt still read `Exploratory OEM Outreach (Wispr / EHRs)`; changed to `(permitted partners)`. All 7 file links now resolve | **CONFIRMED (1 leftover fixed)** |
| 7 | Native warm-light theme + 49/49 suites | `ui/workspace_style.py` present with `#f5f4f0` canvas, `#d98925` accent and `harmonize_legacy_styles()`. **Suite count is 51, not 49** — see §4.4 | **CONFIRMED with a correction** |

### 4.2 Priority 1 — Correction Intent Engine: DELIVERED

`engine/correction_intent.py` (new) + wiring in `engine/writing_intelligence.py` +
`tests/test_correction_intent.py` (new, 23 checks) + registered in
`tests/run_all_tests.py`.

**The capability already existed.** `WritingIntelligence._resolve_self_corrections`
was a set of ordered regexes. It was not a missing feature; it was a **broken**
one. Measured on the pristine tree before any change:

| Input | Before | After |
|---|---|---|
| `I actually enjoyed the movie` | `Enjoyed the movie.` (**meaning destroyed**) | `I actually enjoyed the movie.` |
| `we were actually going to leave early` | `We going to leave early.` (**grammar broken**) | `We were actually going to leave early.` |
| `send this to John sorry Jane` | unchanged (`sorry` was not a trigger) | `Send this to Jane.` |
| `we have five wait six members` | unchanged (`wait` was not a trigger) | `We have six members.` |
| `meet at 2 never mind 3` | unchanged | `Meet at 3.` |
| `call John no wait call Jane` | unchanged — FactGuard saw the trigger's `no` as a dropped negation and silently reverted the whole correction | `Call Jane.` |
| `bring 5 laptops actually 3 laptops and also 2 monitors actually 4 monitors` | `Bring 5 3 laptops and also 2 monitors actually 4 monitors.` (first only, mangled) | `Bring 3 laptops and also 4 monitors.` |

Design rules implemented: a marker word used as an **intensifier** never rewrites
text (function words can never be superseded values); spans are quantity-aware
(`5 copies` → `10 copies`); **every** correction in an utterance is resolved; and
trigger phrases are consumed whole so their internal protected tokens are
reported back to FactGuard as intentional retractions.

Existing contracts held: `test_writing_intelligence.py`, `test_factguard_adversarial.py`
(10/10) and `test_factguard_v2.py` all pass unchanged.

### 4.3 Priority 2 — Real-Voice Baseline: DELIVERED

`scripts/acquire_real_voice_corpus.py` (new), `docs/evaluation/DE_ES_FR_REAL_VOICE_BASELINE.md` (new),
`docs/evaluation/DE_ES_FR_REAL_VOICE_MANIFEST.json` (new), `engine/real_voice_corpus.py`
(language set extended), `tests/test_evaluation_metrics_crosslang.py` (new).

**Corpus:** 120 consented real-human-speech clips (40 de / 40 es / 40 fr) from
Mozilla Common Voice 17.0 `validation` split, CC0, `down_votes == 0`,
`up_votes >= 2`, half of each language deliberately carrying a negation or number.
Audio lives in gitignored `private/corpus/` (21.0 MB). Acquisition is a separate
one-off step; the measurement path stays offline and zero-egress.

**Measured (production `base`):** German **20.17%** WER, Spanish **21.41%**,
French **29.04%** over 40 clips / 367–433 reference words each.
`small`: 9.01% / 13.46% / 19.66%.

**Promotion rule verdict:** Gate 1 (≥10% relative reduction) **passes** on all
three languages. Gate 2 (≥98% fact retention) **fails** — de 95.45%, es 100%,
fr 96.30% — on 22–27 entities per language, which is too small to certify
either way. Gate 3 (P95 stop-to-visible-text ≤ 1.5 s) is **not measured by the
runner**, and `small`'s decode p95 of 2.33–2.42 s exceeds the bound on decode
alone. **Recommendation: do not promote `small` on this evidence.** Full
denominators and every individual entity failure are in the baseline document.

**Three defects were found in the measurement instrument** while running this
baseline, all of which would have produced a *false pass* on the fact gate for
exactly these languages. They are fixed in `engine/evaluation_metrics.py`:
`NEGATION_DICTIONARY` had no `de`/`es`/`fr` entries; Spanish inverted marks and
curly quotes were not stripped from tokens; and a number spelled out in the
reference and rendered as a digit compared unequal.

### 4.4 Test suite status — a correction to "49/49"

The suite now has **51** registered tests, not 49 (Opencode added
`test_correction_intent.py` and `test_evaluation_metrics_crosslang.py`).

On this host the full run is **not** green, and the cause is environmental, not
a code regression:

* **4 suites + 2 end-to-end scenarios fail** — `Text Injection & Clipboard
  Safety`, `End-to-End 5-Cycle Notepad Dictation`, `Cross-Application Injection
  & Focus`, and `18-Scenario Full Specification End-to-End` (scenarios S4 and S5
  only). All fail with *"Notepad document did not acquire focus"*.
* **Root cause:** this machine runs **modern Windows 11 Notepad 11.2410.21.0**,
  which hosts each document in its own process and keeps a
  `Windows.UI.Core.CoreWindow` in the foreground. The harness
  (`tests/notepad_harness.py`) requires the foreground to be in the same window
  hierarchy as the target Notepad, which never happens. The target's own GUI
  thread *does* hold focus on the `RichEditD2DPT` leaf.
* The same harness also **leaks Notepad processes by design** ("never terminate
  a shared Notepad process"). 83 accumulated during this work; each leaked
  window keeps competing for foreground.
* **Proven pre-existing:** a pristine `git archive HEAD` tree, containing none of
  this work, fails the identical suites with the identical messages.
* **One genuine defect was fixed:** `tests/test_orchestrator_state_machine.py`
  waited exactly `10.0 s` for the state machine to return to IDLE while a cold
  `small` model load alone takes ~10.0 s on this host. The budget now covers a
  cold start (`PROCESS_TIMEOUT`), and the suite passes.

**Resolution (2026-10-22, same day):** the harness focus loop was extended with
`tests/notepad_harness.py::_force_foreground` (canonical `AttachThreadInput`
recipe), which brings the target Notepad to the foreground even while a sibling
Store-Notepad shell window holds it. All formerly failing suites now pass on the
interactive desktop. Final full-runner measurement: **51/51 – "ALL TESTS
PASSED", 0 skipped, 0 failed, 463.76 s**.

All suites that this work touches pass: `test_correction_intent.py`,
`test_writing_intelligence.py`, `test_factguard_adversarial.py`,
`test_factguard_v2.py`, `test_evaluation_metrics.py`,
`test_evaluation_metrics_crosslang.py`, `test_multilingual_validation.py`,
`test_multilingual_speech_reality.py`, `test_dissected_upgrades.py`,
`test_orchestrator_state_machine.py`.

### 4.5 Outstanding, not addressed by this work

| Item | Owner |
|---|---|
| Harness leaks Notepad processes per run | test harness |
| Stop-to-visible-text is still not measured, so promotion Gate 3 cannot be evaluated | benchmark harness |
| No spontaneous-speech, noise, overlap or low-volume corpus groups | corpus programme |
| English not re-baselined on this corpus shape | corpus programme |
| `hi` / `ta` / `ml` still have no real-voice audio | corpus programme |
| `C:` had 9.6 GB free during this work (below the 20 GB floor) | workstation hygiene |
