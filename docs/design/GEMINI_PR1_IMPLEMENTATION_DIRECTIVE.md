# Gemini directive: truthful multilingual settings, model lifecycle and transforms

Date: 2026-10-21. Recipient: Gemini working on FlowPilot. Status: implementation handoff, not a completion report or release authorization.

## 1. Assignment and source of truth

Proceed with your proposed PR 1, incorporating the corrections and acceptance requirements below. Deliver a focused, tested local patch. Do not expand this into model training, a general agent, a new companion system or a release rebuild. "PR 1" names the change set; it does not authorize opening a remote PR, committing, pushing or publishing.

Read before modifying:

1. [Current engineering directive](../architecture/CODEX_DIRECTIVE.md).
2. [Speech quality and voice editing plan](SPEECH_QUALITY_AND_VOICE_EDITING_PLAN.md), including its research sources and later phases.
3. [Competitive product specification](FLOWPILOT_COMPETITIVE_PRODUCT_SPEC.md).
4. Applicable repository instructions, current source, callers and tests. Inspect `git status` first; preserve existing work.

The source was rechecked at `0850e4d` (code release commit `a302b80`). The three issues still exist in that inspected source. If concurrent work has changed it, review the diff and adapt; do not overwrite it or reproduce an already completed change. Existing planning-document changes belong to the current worktree and must be preserved.

The actual regression runner is authoritative for suite inventory. Some directive prose still says 38 suites; do not hard-code that historical count or use prior green reports as evidence for a new patch.

## 2. Product intent and boundaries

The immediate user priorities are English, Hindi, Tamil and Malayalam. English mixed with Hindi/Tamil/Malayalam needs its own acoustic evaluation. Later expansion to other widely used languages follows measured quality, not a dropdown count.

The desired product is a local writing assistant: understand speech, respect preferred spellings, and eventually edit a selected passage when explicitly instructed. It is not an autonomous tool-using agent. Ordinary F9 dictation must remain usable without an optional local LLM. Preserve the user's chosen shortcut and conflict protections; do not re-enable retired default bindings.

Keep CPU-local inference, `local_files_only=True`, native Qt UI, the warm pre-roll, focus guards, sequence-protected clipboard behavior, single microphone ownership and current never-store defaults. No automatic model downloads, hidden speech collection, cloud API branches or raw transcript diagnostics. No GUI-thread model loading.

## 3. Track A: Tamil and Malayalam registration and UI integration

Your registry diagnosis is correct, but adding entries alone does not establish production-quality language support.

- Add ISO codes `ta` and `ml`, names Tamil and Malayalam, native labels `தமிழ்` and `മലയാളം`, their script metadata, and LTR direction. Use clean Unicode labels without accidental zero-width characters introduced by copied text.
- Add a backward-compatible quality-status field if needed. The current `LanguageInfo` constructor and both serialization/listing paths do not contain an experimental field: implement and propagate it rather than passing an unsupported keyword.
- Mark these entries experimental visibly in Settings and Setup Wizard; cover the tray or other selectors that consume the registry. Persist ISO codes, not display labels. Avoid duplicating `auto` in Setup Wizard, which currently adds it separately and then iterates a registry that already includes it.
- Retain native script by default. Preserve English code tokens within mixed-language input where the recognizer actually produces them. Do not treat transliteration or translation as the same operation.
- A `recommended_model="small"` value is an evaluation hypothesis, not proof of superior accuracy or authority to download/switch models automatically. Keep the working default unchanged until comparison data exists.
- Native-language prompts require correct Unicode and review. A fluent-looking prompt is not a validated language model or a guarantee of code-switching.
- Reuse the existing session-language/task snapshot. Ensure changes made while speaking apply to the next session, not the current one.

Acceptance: registry lookup, both metadata serialization paths, UI picker visibility, experimental labeling, saved-profile round trip, restart behavior, no duplicated auto option, and explicit versus disabled translation. Include rendering/smoke checks for missing glyphs, not just nonempty strings. Registry tests must not be described as Tamil/Malayalam acoustic accuracy tests.

## 4. Track B: safe model ownership and switching

Tracking `_loaded_model_size` and `_loaded_model_target` is useful but insufficient on its own. A conditional cache reset does not resolve concurrent preload, inference and settings changes.

### Required ownership contract

1. Separate requested configuration from active model identity and pending request. Show ready/loading/deferred/failed state truthfully. Any existing status endpoint reporting a model from config must distinguish requested versus active identity.
2. Define a model key using the resolved asset identity and construction settings such as CPU device, compute type and effective thread count. Keep per-session decode settings (language, task, beam size, VAD and vocabulary snapshot) separate; a language change alone should not reload identical weights.
3. Validate `FLOWPILOT_MODEL_DIR` and generic-folder resolution. A path containing base weights must not be presented as small merely because the requested setting says small. Prefer a pinned model manifest/revision/hash; if identity cannot be established, report a custom/unknown identity rather than inventing one. Do not hash large model files on every utterance.
4. Serialize preload/load/swap through one owner. Construct candidate models off the Qt thread. Document lock ordering; never hold the orchestrator state lock across expensive model construction or call back into it while holding an incompatible lock.
5. Retain the active model for the entire in-flight operation. Protect recording/start/finalization as well as transcription; a setting selected after speech begins must not silently change that session's recognizer or formatting configuration.
6. A transcription is not finished when `model.transcribe()` returns: the current path consumes lazy segments with `list(segments)`. Keep model ownership valid through consumption, fallback and exception cleanup.
7. Protect direct `STTEngine` callers too. The loopback API calls `orchestrator.stt.transcribe()` directly; orchestrator-only deferral does not cover that path.
8. Resolve the idle-to-recording versus idle-to-reload race under a defined ownership transition. If a switch is underway, either keep a verified old model available for a clearly identified session or reject/defer the start with visible feedback. Do not record and later silently reinterpret the audio under an unrelated configuration.
9. Coalesce rapid changes using request generations or equivalent. If a slow small-model load finishes after the user requested base again, its stale completion must not activate small. No unbounded backlog of model loads.
10. On missing/corrupt weights or load failure, leave the previous working model intact where feasible, report the failed request, and reconcile UI/config state. Never claim the requested model is active or retry a doomed load on every dictation. If memory requires unloading first, document the rollback strategy and explicitly report rollback failure.
11. Account for shutdown/cancellation and failed candidates: release ownership on every path, prevent late activation after quit, and avoid unbounded resident models. Do not promise instantaneous cancellation of a blocking native library call.

Use the smallest design that satisfies this contract; a large framework is unnecessary. Prefer a small explicit model/session owner over scattered mutable flags.

### Required lifecycle tests

Use real production lifecycle methods with fake model construction/segments, not mocks that bypass the switching code. Coordinate concurrency with events/barriers and bounded test timeouts rather than hoping sleeps reproduce races.

- Base to small actually constructs/activates the different model; the same key reuses it.
- Effective construction-setting change is recognized; language-only change does not reload weights.
- Requests during recording, finalizing and transcribing leave the active session unchanged and apply only at a safe boundary.
- Concurrent startup preload and first transcription do not load twice.
- Lazy segment iteration holds ownership; exception/fallback paths release it.
- Missing weights and constructor failure retain/recover the old model and report correct active/requested state.
- Rapid base/small/base requests cannot activate stale completions.
- Direct API transcription, config updates and shutdown obey the same ownership rules.
- Wrong/custom asset identity cannot masquerade as a named benchmark model.
- Offline-only loading remains enforced, including failure paths.

Do not label mocked lifecycle tests as measured model performance. Actual base/small acoustic comparison waits for explicitly provisioned local weights and the corpus phase.

## 5. Track C: honest transform results and enforced Apply behavior

Correct your proposal to "fail FactGuard" for unsupported instructions. Unsupported intent and changed facts are different failures. Unchanged text can legitimately pass invariant checks while the requested operation remains unimplemented.

### Result contract

Use a per-request structured result, or a narrowly scoped equivalent that cannot leak previous-request status. Suggested fields:

```text
original_text
candidate_text
status: success | unchanged | unsupported | unavailable | blocked | error
execution_route: deterministic | local_llm | none
guard_status: passed | failed | not_run
reason_code
can_apply: derived from successful execution and passed validation
```

These are proposed semantics, not an existing API. Adapt consistently across engine, UI, tests and other callers; do not change a return type without migrating its consumers. A legacy tuple adapter, if truly required, must not allow a failed result through an apply path. A mutable `last_execution_route` string alone is not sufficient request ownership.

### Required behavior

- Unknown custom instructions with no available local LLM return `unsupported`, preserve the exact input including whitespace/newlines and disable Apply. Show a plain message such as: "This instruction needs the optional local writing model. Your text was not changed."
- Keep explicit deterministic presets working. For custom natural-language aliases, use a narrow exact/anchored allowlist, not substring matching. `"pro" in instruction` can match unrelated requests such as "replace production with staging"; `"list"` can appear inside an identifier. Do not partially execute a compound request by recognizing only one keyword.
- Unknown preset IDs must also fail closed, not run concise formatting.
- Fix the adjacent `_apply_translate_en()` fallback under the same contract: shortening text is not translation. Return unavailable/unsupported unchanged when a required text-translation model is absent. Preserve the independent local speech `task="translate"` feature.
- If an available model times out, throws or returns empty/malformed output, report unavailable/error and leave the original unchanged. Never substitute a different operation and report success.
- If a candidate violates FactGuard, return blocked and prevent application. A warning label while leaving Replace enabled is not an enforcement mechanism.
- Migrate `ui/transforms_view.py`: show execution status separately from invariant status, disable/guard Replace for unsuccessful results, clear stale success styling, and invalidate old results when source text or instruction changes. Check again at the engine/apply boundary; a disabled button alone is insufficient.
- An unsuccessful request must not overwrite the last successful undo/recovery transaction or leave a previous output eligible for Apply. Automatic failure paths must not copy or inject text.
- Preserve typed insertion outcomes. Do not announce an unverified send as a confirmed replacement or blindly send a second Unicode injection after an uncertain first dispatch.

This sprint does not implement "replace Friday with Monday" parsing. Its required result without a capable backend is an honest unsupported operation. Implementing arbitrary voice edits is a later transaction-oriented feature, not a shortcut around this acceptance test.

### Required transform tests

1. No LLM + replace Friday with Monday: exact original returned, unsupported, Apply blocked, zero clipboard/injector calls during execution/apply rejection.
2. Leading/trailing whitespace, blank lines and non-Latin text remain byte-for-byte/character-for-character unchanged on failure.
3. Unrelated instructions containing `pro`, `list`, `work` or `short` do not select an unintended preset. Compound requests are not partially executed silently.
4. Approved deterministic presets/aliases still work without an LLM and still enforce invariants.
5. Unknown preset ID, unavailable text translation, timeout, exception and malformed/empty model output have correct non-success states.
6. A deliberately fact-changing candidate is blocked by the engine and UI; unsupported intent is not mislabeled as an entity mismatch.
7. Success followed by unsupported/error clears previous apply eligibility; editing source/prompt invalidates a prior result.
8. Last successful recovery/undo state is not destroyed by an unsuccessful request.
9. UI and any compatibility adapter cannot turn an unsupported result into a success; no automatic network or clipboard fallback occurs.

Use an injected/mocked local provider. Tests must never call a real installed model server or external service unless explicitly designated integration tests. Protect test configuration with the repository's isolated profile mechanisms.

## 6. Verification, packaging and handoff

Work in small steps: reproduce a defect with a focused test, implement its production fix and caller integration, run that group, then continue. Do not write all three subsystems before testing the first.

Run affected language, STT, session/orchestrator, settings/setup, transforms, network-egress and hotkey regressions, then the current full runner. Include newly added tests in the actual gate; a test file that the runner never executes is not gate coverage. Inspect how each suite is invoked so pytest-style tests are not silently omitted by a script-only runner.

Report actual passed/skipped/failed counts, commands and exit codes. Physical Notepad/VS Code/terminal checks must run on an interactive desktop or remain explicitly unverified for this patch. The user's earlier F9 success is useful prior evidence, not a substitute for validating changed code. Do not manufacture a focused window or bypass production guards to force a green test.

For a source-only patch, do not rebuild the roughly 500 MB distribution repeatedly. After this patch is reviewed and packaging is requested, rebuild once from the settled source, test the exact executable and update hashes/manifests together. Do not change release status or reuse old artifact hashes now.

Deliver a concise review report containing:

1. Files changed and behavior changed, separated by A/B/C.
2. Model ownership/state-transition design and failed-switch behavior.
3. Transform result contract and every migrated caller.
4. Test commands, counts and relevant failure-path evidence.
5. Explicit untested cases, missing model assets or physical-desktop limitations.
6. `git diff --check` result and a statement that unrelated work was preserved.

No "rock solid", "all languages accurate", "zero hallucination" or "better than Wispr" claims based on these unit tests.

## 7. What follows PR 1: retain this context, do not implement it all now

### Real-voice comparison

Use the linked speech-quality plan for the corpus schema and scoring. First compare multilingual base and small INT8 under identical settings on the inspected i5-12500H / approximately 16 GB workstation. Keep the current default until evidence supports a change.

Start with 40 deliberately recorded development samples across four languages; then use a separate held-out set of at least 50 utterances per language with several speakers and dedicated English-mixed-language groups. These are starting evaluation sizes, not statistical certification. Recordings require explicit consent and must not be harvested from everyday dictation. No model downloads or new recording begins as part of PR 1.

Measure raw WER against one spoken reference, formatted quality separately, Unicode-aware CER, exact developer/factual errors, cold/warm timing, loaded memory, first-paste success and correction effort. Existing 15-trial SAPI results are synthetic regression evidence, not real-voice multilingual validation. Processing latency is not speech-end-to-visible-text latency. Resolve VB-Cable endpoints dynamically; prior device numbers are not stable identifiers.

### Vocabulary before fine-tuning

The active STT prompt currently concatenates all personal dictionary terms without a tokenizer budget. Later add explicit correction teaching, scoped aliases, ranked/bounded hints, negative controls and deletion persistence. Do not call a dictionary update model training or silently watch user edits. Fine-tuning comes only after repeatable acoustic errors survive capture checks, model selection and vocabulary improvements.

### Safe editing before rich rewriting

Start future edit-by-voice work in the owned Scratchpad with explicit edit activation, a known selection, preview and guarded undo. External editors need target identity, revision/range checks, one-use transactions, secure-field exclusion and bounded context acquisition. "Remove this part" without an identified selection must ask rather than guess. Preserve unrelated facts; an explicit authorized date change is not permission to disable all semantic guards.

Reuse the existing optional local provider for richer writing only after these contracts hold. Loopback transport alone does not prove the backend is offline. Require local weights, explicit model identity, backend egress checks, bounded context and a total deadline. ASR and LLM memory/CPU competition needs measurement. No cloud fallback or tool-executing agent.

The linked plan contains model-card research for Whisper, Distil-Whisper, Moonshine, IndicConformer, Indic-Transcribe and an optional compact writing model. Those are candidates with language/runtime/license limitations, not tested drop-in replacements or mandates to install them.

### Companions and competitor claims

Original optional companions remain a separate track using the existing native renderer. The research verified Aqua Voice's desktop pet and Wispr's language/Command Mode features, not Wispr-branded Naruto, Harry Potter or Star Wars packs. Do not distribute copied franchise assets or make unsupported parity claims. Branded packs need a separate rights review. Speech reliability is the immediate priority.

## Completion instruction

Proceed with Tracks A, B and C plus their required tests. Report source changes and evidence for review when those are complete. If real-model or interactive verification is unavailable, finish the safe deterministic work and state exactly what remains unverified; do not disguise missing evidence as a pass. Keep later research phases as separately scoped follow-up work.
