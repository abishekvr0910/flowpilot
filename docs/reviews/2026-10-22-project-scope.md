# Project scope review, 2026-10-22

**Verdict:** Changes requested.

**Scope:** The five current files in `docs/scope/`, reviewed directly against repository source and project release requirements at commit `367185c`. The scope files are untracked. This is a review of the plan and its claims, not a full application audit or release approval.

**Method:** Read the files afresh without using earlier conversation conclusions or earlier review reports as evidence. An independent reviewer with a fresh context also checked implemented feature boundaries against source. No application code or scope files were changed. Existing reported test results were not rerun or independently recertified.

## Summary

The scope gives a useful map of FlowPilot and usually distinguishes present code from verified product quality. Its release criteria lose several requirements already established elsewhere in the repository. It also postpones external editing safety even though a related replacement and revert path is already exposed to users. Correct those omissions before using this as an implementation and release handoff.

## Major findings

### 1. Existing external replacement and revert need a release prerequisite

**Location:** `docs/scope/voice.md:51`, especially the intent at line 53 and completion criterion at line 55.

**Problem:** Feature 22 treats safe editing outside the scratchpad as future exploration. Current selected text transforms already replace and revert text in external applications. The scope acknowledges selected text transforms in `docs/scope/workspace.md:13`, but does not bring their existing behavior into the planned safety work.

**Evidence:** `desktop_app.py:238` captures an external selection. `ui/transforms_view.py:346` calls `replace_selection`, and line 364 calls `revert_last_transform`. In `engine/transforms_engine.py:415`, replacement checks transform eligibility and then injects into a stored window handle; it does not recheck the original document revision or selected range. The revert path at line 442 reinjects original text without verifying that it is replacing the prior edit. Both paths reduce `InjectionResult` to a boolean. `engine/text_injector.py:40` makes `SENT_UNVERIFIED` truthy, while `ui/transforms_view.py:366` reports that original text was restored.

**Impact:** A user can change the selection while preparing a transform, then apply into a different span. A revert can insert text at the current cursor and still present a restoration message without verified delivery. Future editor integration could be completed while this existing route remains outside the work.

**Suggested correction:** Add remediation or temporary disablement of the current external Replace and Revert paths as a prerequisite for release. Carry revision, selection, target identity, and truthful delivery requirements through those entry points. Keep richer new spoken editing in the later feature phase. This finding is based on source tracing, not a physical editor reproduction.

### 2. Distribution completion does not inherit the mandatory release gate

**Location:** `docs/scope/release.md:33`.

**Problem:** The completion criterion requires explained contents, offline startup, signature disclosure, and matching hashes. It omits the strict regression gate, CI for the exact source, verification of the final signed bytes, and preservation of existing user profiles during upgrade. There is no explicit link making the existing release guide a prerequisite.

**Evidence:** `docs/archive/CODEX_DIRECTIVE.md:18` requires `tests/run_all_tests.py --require-all` and says skipped or failed strict checks block promotion. `docs/release/flowpilot_build_and_release.md:32` requires CI for the intended commit and interactive hardware checks. Lines 44 and 46 require verification after signing or rebuilding. Line 54 requires upgrades from an existing profile with settings preserved; line 57 requires a rollback record with tested limitations.

**Impact:** The distribution item can satisfy its written scope while missing checks that the project already considers mandatory. A clean profile test also cannot establish that a returning user's privacy settings, vocabulary, or other saved data survive an upgrade.

**Suggested correction:** Make the release guide and release evidence template explicit prerequisites. Include exact candidate identity, the strict gate, required physical checks, final artifact verification, upgrade preservation, and rollback limitations in the completion criterion. Keep detailed execution steps in the release spec.

### 3. The plan does not assign runtime performance validation

**Location:** `docs/scope/voice.md:33` and `docs/scope/voice.md:41`.

**Problem:** The two planned core evaluations cover accuracy and delivery outcomes, but neither owns responsiveness or resource use. Distribution work concerns download size. All three can complete while dictation is too slow or consumes too much memory on the intended computers.

**Evidence:** `docs/release/RELEASE_EVIDENCE_TEMPLATE.md:25` explicitly asks for stop to visible text timing, sample count, p50, p95, and failures. `docs/testing/FLOWPILOT_BENCHMARK_PROTOCOL.md` sections 1 and 4.3 include timing and processing efficiency. `tests/test_model_benchmarks_extended.py:209` onward already measures model processing time and memory, but that does not by itself prove the complete interactive journey.

**Impact:** A central product property has no planned completion condition. Choosing a larger language model could improve accuracy while making ordinary dictation unusably slow, without failing this scope.

**Suggested correction:** Add performance to the release evaluation scope. Define supported hardware and model combinations, cold and warm behavior, stop to verified visible text timing where measurable, and loaded and peak resource use. Set budgets in the evaluation spec. Keep dispatch timing distinct from physically observed delivery, and do not infer speed from offline self test duration.

## Minor finding

### 4. Pilot instructions need reconciliation before the pilot starts

**Location:** `docs/scope/release.md:23`, with documentation review scheduled separately at line 39.

**Problem:** The pilot item has no explicit prerequisite to update the materials testers will receive. Existing pilot instructions conflict with the privacy defaults described in the scope and current source.

**Evidence:** `docs/pilot/PILOT_QUICKSTART.md:8` says completed dictations and audio are saved by default. `engine/config.py:41` sets `save_history_text` to `False`. The pilot checklist also expects vault WAV and text after dictation without separating history enabled and disabled cases. The quickstart describes a source checkout rather than the exact candidate ZIP proposed for the pilot.

**Impact:** Testers can misunderstand retention or report correct absence of history as a failure. Results can also come from a different source state than the intended candidate.

**Suggested correction:** Include candidate specific pilot instructions and separate history on and off expectations in the pilot readiness checklist. Reuse and reconcile the existing pilot files before sending testers to them.

## Strengths

- Existing implementation is clearly distinguished from proof on customer hardware.
- Experimental Tamil and Malayalam support is described accurately.
- Scratchpad edit guards are not represented as universal editor support.
- Companion rule proposals are correctly distinguished from rules that control the live HUD.
- The plan keeps mobile expansion and uncertain windowed video detection outside the immediate release work.

## Verification performed

Read all five scope files, traced relevant source paths, checked their local Markdown links, and compared release criteria with the current directive, release guide, evidence template, and pilot materials. No physical input was dispatched and no full regression suite was run. There is no new executable behavior in the reviewed change that calls for new tests. The findings identify scope corrections and one existing implementation path that merits focused code review and behavioral tests.

## Recommended next revision

Bring current external transform safety into the release prerequisites. Make the existing strict gate and upgrade requirements explicit. Add performance to the evaluation scope and correct pilot instructions before distribution. Then proceed with pilot specification and the companion visibility work using the revised release boundary.
