# Gemini handoff: scope corrections and release readiness

**Date:** 2026-10-22
**Recipient:** Gemini implementation partner
**Baseline inspected:** `367185c`, local `master`
**Status:** Source remediation and isolated development build verified; field and release gates remain open. See the [implementation report](../reviews/2026-10-23-remediation-verification.md) for actual results and limits.

## Purpose

You are correcting four findings from a fresh review of the project scope and source. First address an existing external text editing failure. Then bring the scope, release criteria, performance evidence, and pilot instructions into agreement.

The requested result is a reviewable implementation with evidence. This document does not establish that a fix has shipped or that the candidate is ready for public distribution.

## Start from the actual workspace

Read root and relevant nested `AGENTS.md` files, inspect the current branch and worktree, and record the source commit you actually change. Recheck the source paths below because another developer may have moved them. Preserve unrelated changes and untracked files.

The reviewed source was `367185c`. If your baseline differs, explain what changed before applying the findings. Keep existing candidate bytes and their manifest tied to their own source identity. A source fix does not update an older executable.

## Findings and evidence

### 1. External transforms bypass a guarded refusal

In [TransformsEngine](../../engine/transforms_engine.py), `replace_selection()` and `revert_last_transform()` call `TextInjector.inject_with_status()`. A false result then triggers `inject_unicode_sendinput()` without distinguishing focus loss from a recoverable clipboard problem.

The direct Unicode helper does not repeat the guarded injector's full foreground verification before dispatch. A refusal intended to prevent typing into an uncertain target can therefore lead to another input attempt.

There is also a reporting defect. [InjectionResult.__bool__](../../engine/text_injector.py) returns true for `SENT_UNVERIFIED`. Both transform methods collapse this into success, and [TransformsView](../../ui/transforms_view.py) can announce that text was restored.

The external transform path does not carry the scratchpad's document revision and selection transaction guards. Checking an HWND or seeing inserted text alone does not prove that an intended replacement or undo occurred.

A controlled probe patched both injector methods, so no real keys were sent. It observed:

| Guarded injector outcome | Operation | Direct Unicode helper called | Transform method returned |
|---|---|---|---|
| `FAILED_RECOVERY_AVAILABLE`, simulated focus loss | Replace | Yes | `True` |
| `FAILED_RECOVERY_AVAILABLE`, simulated focus loss | Revert | Yes | `True` |
| `SENT_UNVERIFIED` | Replace | No | `True` |
| `SENT_UNVERIFIED` | Revert | No | `True` |

The existing eight tests in `tests/test_honest_transforms.py` passed during that review. They cover transform eligibility but do not cover this refusal and status propagation path.

### 2. The scope omits existing release requirements

The completion criterion for distribution in [release scope](../scope/release.md) omits mandatory requirements already recorded in the [engineering directive](CODEX_DIRECTIVE.md), [release guide](../release/flowpilot_build_and_release.md), and [release evidence template](../release/RELEASE_EVIDENCE_TEMPLATE.md).

Those requirements include the strict regression gate, CI for the intended commit, physical Windows checks, verification after signing, preservation of existing profiles during upgrade, and documented rollback limits.

### 3. Runtime performance has no assigned scope item

The [voice scope](../scope/voice.md) plans accuracy and paste outcome evaluation. It does not assign stop to visible text timing, supported hardware and model combinations, or loaded resource measurement. The release evidence template already asks for timing samples and p50 and p95 results.

### 4. Pilot instructions describe the wrong history default

[PILOT_QUICKSTART.md](../pilot/PILOT_QUICKSTART.md) says completed transcripts and WAV audio are saved by default. Current `engine/config.py` sets `save_history_text` to `False`. The checklist expects vault data without separating history enabled and disabled cases. The quickstart also describes a source checkout rather than the fixed candidate archive proposed for testing.

## Work package 1: external transform safety

### Required behavior

1. A guarded refusal ends the input attempt. Do not call a raw typing helper after `FAILED_RECOVERY_AVAILABLE`, `CANCELLED`, `ERROR`, lost focus, or an invalid target. Any legitimate clipboard fallback belongs inside a path that performs the same target checks.
2. Preserve the structured injection outcome through the transform engine and UI. Reuse `InjectionResult` for input delivery rather than converting it into a generic success boolean. Update every affected caller and test together.
3. `SENT_UNVERIFIED` produces a neutral message such as `Sent, please check`. It must not produce a confirmed replacement, restored document, or successful undo message.
4. A refused operation preserves recovery text in memory. It does not overwrite the system clipboard merely to offer recovery. Copy is an explicit user action.
5. Replacement and revert require verified target identity, the expected document revision, and the expected selection or edited span. A confirmed paste alone is insufficient evidence of an atomic edit.

### Recommended immediate scope

Keep external Replace and Revert unavailable for targets that cannot satisfy those checks. Explain the limitation in the UI and keep preview and Copy available. Preserve the existing guarded scratchpad editing path.

Do not turn this repair into universal external editor support. If reliable revision and selection verification needs a new target adapter, record that as later work. Until it is implemented and tested, refuse external mutation through that route. Enforce the restriction in the backend as well as the buttons.

A genuine revert must identify the exact prior applied edit, confirm the document still matches its expected post edit revision, and restore that edit once. Reinserting old text at the current cursor is not a revert.

### Required tests

Extend existing focused suites where practical:

| Scenario | Required assertion |
|---|---|
| Guarded injector refuses after focus loss | No direct Unicode fallback, retry, or second input dispatch occurs |
| Missing, closed, or changed target | Operation refuses and recovery text remains available |
| Injector returns `SENT_UNVERIFIED` | Engine and UI retain that outcome; no restoration or confirmed edit message |
| External mutation has no verifiable transaction | Backend refuses; UI offers preview and Copy |
| Selection or document changes after planning | Apply and revert refuse without input dispatch |
| Revert is invoked twice | The consumed edit cannot be applied again |
| Clipboard changed by the user during an abort | Newer clipboard contents remain intact |
| Scratchpad edit and undo | Existing guarded transactions still work |

Patch physical input functions in unit tests. A test should fail if an unexpected dispatch is attempted. Mocked tests cannot establish physical paste success.

### Relevant files

`engine/transforms_engine.py`, `engine/text_injector.py`, `ui/transforms_view.py`, `engine/voice_editor.py`, `ui/scratchpad_view.py`, and their actual callers. Start with the transform methods and their UI; change the shared injector only where the required behavior demands it.

## Work package 2: scope and release criteria

Update the existing scope in place. Keep its useful feature inventory and preserve the distinction between implemented code and field evidence.

1. Inventory the existing external selected text controls clearly. Move their safety repair into the release prerequisites. Keep broader new external voice editing as a later feature.
2. Make the release guide and evidence template explicit dependencies of release completion.
3. Require the strict runner for the candidate: `python -X utf8 tests/run_all_tests.py --require-all`. A failed or skipped strict gate prevents release promotion. Hosted skips must remain visible and need physical evidence before signoff.
4. Require green CI for the intended source commit, the repository's integration checks, and interactive Windows hardware and editor verification.
5. Build before packaged binary checks. After signing or changing packaged bytes, rerun the relevant checks against the resulting artifact and compute fresh hashes.
6. Include both a clean profile and an upgrade from an existing supported profile. Check privacy choices, dictionary and snippets, companion settings, and existing stored data. Record any intentional migration.
7. Record the prior download and downgrade limits. Do not promise that a changed profile can be read by older code unless tested.
8. Keep existing RC2 results historical. Record new source and artifact evidence separately when a new candidate is built.

Do not mark a scope feature complete because its plan was written. Keep failures, skipped checks, and pending physical validation visible.

## Work package 3: performance evaluation ownership

Add a clearly owned performance outcome to the existing voice evaluation and release scope, or add a small dedicated feature if that reads more clearly. Reuse the current evaluation code where possible.

### Measurement contract

- Record exact CPU, logical processor count, RAM, Windows version, selected model and revision, thread configuration, build commit, and whether the run uses source or a packaged binary.
- Record cold startup and first transcription separately from warm dictation.
- For actual delivery, time from the user's stop action to text observed in the target document. Record p50, p95, sample count, failures, and recovery attempts.
- An unreadable target has no measured visible text endpoint. Label dispatch or processing duration accurately; do not substitute it for confirmed delivery latency.
- Keep speech recognition duration, formatting duration, and injection duration separately available for diagnosis.
- Measure total FlowPilot process memory with the model loaded, peak memory during use, and CPU during idle, recording, processing, and companion rendering. Count related processes consistently.
- Exercise short bursts and a longer session. Check for queue buildup and continuing memory growth after warmup. Test the model choices being advertised, including the accuracy versus speed tradeoff.

Agree and record supported hardware classes and pass thresholds before judging the results. Existing project performance goals can inform the targets; historical numbers from another build are not current measurements. If the available machine cannot establish a hardware class, leave that class unverified.

Separate generated test speech from real speaker results. If a paired Wispr benchmark is not executed with matching inputs and metric endpoints, describe the results as FlowPilot measurements.

## Work package 4: pilot materials

Update `docs/pilot/PILOT_QUICKSTART.md` and `docs/pilot/PILOT_TESTING_CHECKLIST.md` before pilot distribution.

1. Describe `save_history_text: false` as the fresh profile default. Explain that existing profiles retain their saved choice.
2. Explain that the last recovery text remains in memory, while prior history, meetings, scratchpad, and logs have separate lifecycles. Turning history off does not erase older files.
3. Split retention checks into history disabled, history enabled, and existing saved data cases.
4. Give instructions for the exact candidate being tested, including its version and hash. Keep source checkout testing as a distinct workflow.
5. Record first attempt delivery, unverified dispatch, safe refusal, recovery, and duplicate insertion separately.
6. Use consenting participants and non sensitive fixtures initially. Do not collect raw transcripts by default for diagnostics.

## Build plan and verification

Prepare reviewable changes in this order:

1. **Transform safety repair:** reproduce the current refusal bypass in a failing regression, repair status and dispatch behavior, and cover UI messages and scratchpad compatibility. Resolve or disable unguarded external mutations before pilot use.
2. **Scope and pilot corrections:** make the release prerequisites explicit and reconcile privacy and candidate instructions. Verify links and check the current test list before changing any suite count.
3. **Performance evidence:** define the measurement protocol and support matrix, run the measurements available in your environment, and label unavailable physical measurements pending.
4. **Candidate validation:** after source review, build any requested new candidate from the recorded source. Run focused tests, the full runner, repository integration tests, packaged smoke, clean cache offline transcription, upgrade checks, and required physical desktop checks as applicable to the candidate.

Use the current repository commands and dependencies. Preserve local inference, focus protection, native Qt rendering, and explicit storage choices. There is no need to install capture tools or add a new model for this repair.

This handoff does not authorize a push, tag change, or public release. Prepare patches and evidence for review. If your test session cannot access the interactive Windows desktop, report that limitation with the exact skipped cases. Do not dispatch blind input or replace a failed assertion with a synthetic pass.

## Completion report to return

Provide a short summary followed by:

1. Source baseline and resulting change identity, plus the changed files.
2. Each of the four findings, what changed, and the evidence that closes it.
3. Exact commands, pass, fail, and skip counts, and the new regression names.
4. Whether external Replace and Revert are safely supported or deliberately unavailable, and how the UI explains that choice.
5. Performance measurements with their definitions and hardware, or explicit pending measurements.
6. Artifact hashes and signing status only if a new candidate was actually built and checked.
7. Remaining blockers and the next concrete action.

Completion means the required behavior is demonstrated and the scope reflects the evidence. A green focused suite, a written plan, or an executable that starts cannot establish all of these outcomes alone.
