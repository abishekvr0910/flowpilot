# FlowPilot handoff review — 2026-10-21

## Decision

Useful foundations, but the submitted completion summaries overstated integration
and evidence. Source fixes have been applied locally. This is **not a release
approval**, a Wispr Flow comparison, or proof of multilingual recognition quality.
No commit, push, release publication, model download, or executable rebuild was
performed in this review.

Reviewed local history includes `12f92f1`, `98c0a05`, `1b7c016`, and `46bdcbc`.
The separately mentioned `flowpilot_companion_prototype_and_sketches_review.md`
was not found in this checkout. Kiki source and committed preview images were
inspected; Taro and Mochi should remain labelled concepts, not delivered characters.

## Confirmed defects and local fixes

| Area | What actually failed | What changed |
| --- | --- | --- |
| Evaluation evidence | Missing WAVs were replaced with their reference transcripts, creating artificial zero-WER results. | Missing recordings now produce null metrics and an incomplete run, without loading STT. The tracked report was regenerated: **0/40 evaluated, 40 missing audio**. |
| Corpus handling | Consent defaulted to true; relative paths depended on working directory; a missing requested manifest silently fell back. | Recorded audio requires explicit consent, paths are manifest-relative, missing manifests fail, duplicate IDs fail, and text-only template consent flags are false. |
| Metric safety | Substring matching accepted `12` inside `120`, `not` inside `notebook`, lost duplicates and missed CLI flags. | Exact extracted entities, occurrence counts, additions and ordering are checked. This remains an entity heuristic, not full semantic proof. |
| Report privacy and wording | Reports included transcripts by default and labelled a final RSS sample as peak usage. | Transcripts require `--include-text`; default output is ignored scratch storage. RSS and latency boundaries are stated honestly. |
| Edit transactions | A copied transaction could replay; mutated candidate text could apply; current selection was ignored. | Engine-owned sealed snapshots, locked one-use issuance, source selection and target checks, cancellation and superseded-preview rejection. |
| FactGuard | Preset edits could bypass failed verification because code looked for a nonexistent `violations` key and allowed an empty search term. | Presets must pass FactGuard. Explicit replace/delete/append operations use sealed exact splices, preserving text outside their authorized delta. |
| Undo | Undo transactions entered the same undo stack, causing subsequent undo to toggle forward. | Undo marks the original transaction undone and walks back through prior applied edits. History is bounded per target. |
| Editor boundaries | Invalid selections were silently clamped; external target type was accepted without a verified field adapter. | Reject invalid ranges. External voice editing is disabled; owned Scratchpad only. Process/title heuristics are not password-field verification. |
| Scratchpad integration | Qt UTF-16 positions were used as Python string offsets; stale previews could remain applicable. | Convert offsets, isolate target IDs, invalidate previews on text/selection/instruction changes, and require explicit Apply for deletion. |
| Vocabulary scope | Live WritingIntelligence did not pass language/profile into dictionary replacement. Unknown scope permitted restricted terms. | Scope flows through cleanup and ASR orchestration; unknown context excludes restricted entries. Unfiltered library listing remains separate. |
| Decoder budgets | Oversized base prompts escaped the limit; hotwords were only count-limited; hybrid could duplicate personal terms. | Bound base, combined prompt and hotwords; check the loaded model tokenizer before decode; use a conservative byte upper bound if unavailable. |
| Kiki integration | Renderer code existed, but Kiki was absent from the picker and HUD built-in dispatch. Listening ignored microphone amplitude. | Added selectable prototype entry, palette options, HUD route and context-menu entry; audio-driven badge response and display-grid snapping. |
| Animation evidence | Preview script duplicated sprite definitions and demonstrated animation separately from production code. | Preview sheets/GIF now call the production renderer. Confirmation settles after 1.2 seconds using state-relative clocks; reduced motion retains state distinctions. |
| Test/runtime hygiene | Scratchpad/personalization bypassed config isolation; child tests could crash printing Unicode window titles. | Respect isolated config storage, run child tests with UTF-8, and remove window-title logging from dictation startup. |

## Verification actually performed

1. Added hardware-free adversarial checks before fixing production paths. Initial
   result: **15 failed, 1 passed**. Tests were expanded during integration to 27
   checks in `tests/test_review_integration.py`.
2. Final focused pytest run: **56 passed**, one existing warning about a legacy
   test returning a boolean. Includes the new checks and original PR2/PR3/PR4,
   Kiki and personalization tests. These are not 56 independent live dictations.
3. Full registered runner: **47 suites, 41 passed, 6 failed, 0 skipped**, 182.35s.
   Three failures were personalization's old unscoped test contract and two
   Unicode-console crashes. After correcting those, their separate rerun was
   **3/3 passed**, 24.97s. Do not describe these separate runs as a clean 47/47 gate.
4. Three physical suites remain unresolved in this environment:
   - `test_notepad_dictation_e2e.py`
   - `test_cross_app_injection.py`
   - `test_final_specification_e2e.py` (S4 and S5)

   They reported `FOCUS_UNAVAILABLE` / document focus not verified for modern
   `NotepadTextBox`. The desktop detector returned interactive, so these are
   failures, **not headless skips**. No focus guard was weakened and no WM_PASTE
   rescue was added. The separate text-injector suite passed in that run.
5. Regenerated and visually inspected the production-renderer contact sheet.
   Different poses, palettes and scale samples are present. No 60 FPS, sub-0.2ms,
   RAM budget, attractiveness or user-preference claim is established by pixel tests.
6. Packaging smoke passed against the executable already on disk. That binary
   predates these changes; this does not validate packaging of the new source.
7. The instrumented egress suite passed. No whole-system traffic capture or new
   Wispr measurement was performed.

Local logs (ignored): `scratch/codex-review-gate.log` and
`scratch/codex-review-recheck.log`. Tests used an isolated config directory and
temporary storage. Filesystem sandbox restrictions prevented some temporary-file
tests initially; approved execution outside that sandbox allowed them to run.

## What remains / next Gemini assignments

### A. Finish the reliability gate before rebuilding

- Reproduce the three physical failures on a quiet interactive desktop using
  disposable test-owned documents. Record root HWND, focused child, thread IDs,
  desktop identity and readable document result; do not log document text/titles.
- Distinguish foreground-root ownership from actual editor/caret ownership. Do
  not accept unknown focus or replace the product paste path with harness-only
  WM_PASTE. Preserve clipboard sequence guards and honest unverified outcomes.
- Add a regression for the specific focus mechanism discovered. Run the full
  registered gate, with pass/fail/skip counts and first-attempt/recovery outcomes.
- Rebuild only after that gate. Re-test the extracted package, refresh hashes,
  and label any remaining skips or failures. No automatic publication.

### B. Obtain real language evidence

- Collect deliberately recorded, consented clips for English, Hindi, Tamil and
  Malayalam using the 40-item template as an initial smoke set. Keep recordings
  and private reference text out of git. Include mixed-language, quiet, noise,
  negation, number and developer-identifier examples.
- Have fluent speakers verify both spoken and desired-writing references. Split
  tuning examples from held-out tests; do not tune aliases against the same clips
  later presented as independent evidence.
- Compare already-provisioned local `base` and `small` under identical conditions.
  Report raw WER/CER, annotated critical facts, cold/warm decode, and separately
  measured stop-to-visible-text latency. A 40-prompt template alone proves none of
  those acoustic outcomes. No fine-tuning or new language quality claims yet.

### C. Finish voice-editing UX without becoming an agent

- The current Scratchpad has a command parser, preview, Apply and programmatic
  `execute_voice_command()` entry. A direct spoken-command routing flow was not
  demonstrated by these tests; calling that method with a string is not a live
  speech-to-edit test.
- Make command capture an explicit, visibly separate mode. Dictating into the
  document must not silently become an editing instruction. Show the recognized
  instruction and diff before Apply. Ambiguity keeps the original text untouched.
- Keep external editing disabled until there is a verified selection/document
  adapter with password-field checks and bounded UIA calls. No terminal editing.
- Test end-to-end spoken command -> recognized instruction -> preview -> Apply
  -> undo, including changed selection, emoji/Indic offsets, cancellation and
  microphone stop/restart. Safety tests must call production implementations.

### D. Continue original character design as an independent track

- Kiki is a functioning pixel prototype, not finished anime-quality animation.
  Taro and Mochi are concept descriptions until actual assets/renderer paths exist.
- Have a few target users choose silhouettes at actual 48–72px display sizes.
  Improve readability and personality before adding more characters. Preserve
  distinct listening, processing, unverified and recovery cues.
- Use original characters; keep asset provenance and attribution. Do not market
  recognizable franchise characters as FlowPilot-owned assets.
- Keep animation native and local, passive windows non-activating, and reduced
  motion meaningful. Measure renderer cost and idle CPU separately from ASR.
- Integrate only reviewed changes with tests and production-renderer previews.
  No shared-worktree concurrent edits to engine, HUD or renderer files.

## Plain-language assessment

We now have a safer editor, better-integrated vocabulary and a selectable Kiki
prototype. We still need real recorded-language testing and reliable desktop
focus validation. Those improvements matter more than another feature count or
an unsupported claim that FlowPilot already beats Wispr Flow.
