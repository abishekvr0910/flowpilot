# Voice and writing

These features cover the path from sound to safe text. The existing code is a foundation, not a guarantee of equal quality across microphones, languages, or target apps.

## Existing foundation

### 1. Offline capture and speech engine · existing

Capture with a warm audio buffer, local activity detection, and local CPU speech recognition. Code in `engine/audio_recorder.py`, `engine/silero_vad.py`, and `engine/stt_engine.py`.

### 2. Dictation controls and session lifecycle · existing

Support configurable hotkeys, toggle or hold behavior, and clean ownership of each recording session. Code in `engine/hotkey_service.py`, `engine/orchestrator.py`, and `engine/session.py`.

### 3. Writing quality and personal vocabulary · existing

Clean spoken text conservatively, preserve critical facts, and use user-chosen vocabulary and snippets. Code in `engine/writing_intelligence.py`, `engine/context_processor.py`, `engine/personalization.py`, and `engine/correction_intent.py`.

### 4. Text insertion and recovery · existing

Try to insert at the intended cursor, report whether delivery was verified, and keep recoverable text when it was not. Code in `engine/text_injector.py` and `engine/orchestrator.py`. This is not a measured 99.9 percent success claim.

### 5. Multilingual modes and translation · existing

The registry includes English, Hindi, Tamil, Malayalam, and other language choices. Tamil and Malayalam are marked experimental. Local translation and model choice exist, but real speaker quality remains a separate gate. Code in `engine/language_registry.py` and `engine/stt_engine.py`.

### 6. Bounded voice commands and editing · existing

The current scratchpad can plan and apply guarded edits with a preview. External Replace and Revert are unavailable in the backend and UI until a real revision and selection adapter exists. Caller supplied transaction labels cannot authorize input. Preview and Copy Output remain available. Optional local model transforms have an explicit unavailable path. Code in `engine/voice_editor.py`, `engine/transforms_engine.py`, and `ui/scratchpad_view.py`.

## Next release evidence

### 26. External transform safety repair · done

Prevent unsupported external replacements and revert attempts from dispatching input. Keep recovery text in memory without touching the user's clipboard. Keep ordinary dictation and guarded scratchpad edits available.

**Done when:** backend and UI refuse external mutation, forged transaction labels cannot bypass the restriction, and scratchpad revision checks and undo still pass regression tests. The current source and RC8 include this repair; older candidate evidence does not verify later changes.

- [x] Implement the bounded repair: `/develop external transform safety`
- [x] Verify backend refusal and Qt control behavior: `/check verify external transform safety`
- [x] Protect dispatch, status, recovery, and scratchpad behavior: `/test external transform safety`

Plan and evidence: [remediation and release gate review](../reviews/2026-10-24-remediation-and-release-gate.md). Code in `engine/transforms_engine.py`, `ui/transforms_view.py`, and `tests/test_honest_transforms.py`.

### 28. Persistent microphone selection · in-progress

Keep the chosen physical input stable when Windows device enumeration changes. Settings currently persists a persistent endpoint contract (`name`, `host_api`, `max_channels`), and dynamic runtime resolution disambiguates host APIs (WASAPI, DirectSound, MME). Disconnected devices resolve to an explicit sentinel (`DEVICE_MISSING_SENTINEL = -9999`) preventing silent fallback to internal default mics.

**Done when:** a saved device is resolved by a persistent identity, duplicate names remain distinguishable, a missing input is reported honestly, explicit system default selection works, and reconnect or restart cannot silently select a different device. Existing deferred switching and recorded frames remain safe.

- [x] Design it (spec): [spec 0002](../specs/0002-persistent-audio-input-identity.md)
- [x] Implement the persistent endpoint contract and resolver: `engine/audio_devices.py`
- [x] Guard missing devices against silent fallback: `engine/audio_recorder.py` and `engine/orchestrator.py`
- [x] Expose host API and disconnected indicators in UI: `ui/settings_dialog.py` and `ui/setup_wizard.py`
- [x] Regression tests: `tests/test_audio_devices.py` (20 tests passed on 24 October 2026)
- [ ] Confirm disconnect, reconnect, default changes, and index renumbering on physical hardware with the exact packaged candidate.

Code in `engine/audio_devices.py`, `engine/audio_recorder.py`, `engine/orchestrator.py`, `engine/config.py`, `ui/settings_dialog.py`, `ui/setup_wizard.py`, and `ui/scratchpad_view.py`.

### 15. Real speaker language evaluation · planned · needs a decision

Measure speech from consenting native speakers in English, Hindi, Tamil, and Malayalam, including mixed language and developer terms. Keep synthetic speech in a separate diagnostic group.

**Done when:** each advertised language has a published sample count, corpus rules, word and character error results, critical fact errors, hardware, model, and failure examples. Include spontaneous and mixed language speech, with speakers separated between development and final evaluation. Do not promote an experimental language from synthetic tests alone.

- [ ] Design it (spec): `/architect real speaker language evaluation`

### 16. Real application paste reliability · planned · needs a decision

Measure first attempt delivery and safe recovery across actual Windows editors, browsers, terminals, and slow apps. Include focus loss, elevation limits, and rich clipboard behavior.

**Done when:** a repeatable app matrix records verified paste, unverified dispatch, safe abort, duplicate insertion, recovery, and clipboard preservation separately, with enough trials to support any public reliability claim.

- [ ] Design it (spec): `/architect real application paste reliability`

### 25. Runtime latency and resource evaluation · in-progress

Measure and record cold startup, warm dictation latency (stop action to visible document text: p50 and p95), memory footprint with model loaded, and CPU consumption across defined hardware tiers.

**Done when:** timing boundaries, sample counts, failures, model identity, and hardware are recorded; real visible delivery and the resource phases have evidence on each supported class. Missing desktop measurements remain pending and synthetic fixtures remain separate from real speech.

- [x] Define measurement boundaries and remaining gates: [runtime protocol](../testing/RUNTIME_PERFORMANCE_PROTOCOL.md)
- [x] Extend the existing evaluator with cold and warm processing summaries and hardware metadata: `/develop runtime evaluation evidence`
- [x] Capture and label an initial synthetic source processing smoke: [raw evidence](../evaluation/RUNTIME_PROCESSING_SMOKE_2026-10-22.json)
- [ ] Verify physical delivery, recording, companion load, and a long session on supported hardware: `/check verify runtime latency and resource evaluation`
- [ ] Review the resulting support matrix and regression budgets: `/test runtime latency and resource evaluation`

## Product quality

### 31. Approved local correction learning · planned · needs a decision

Let a user explicitly teach a recurring correction and review its language and app/profile scope. Build on current vocabulary, aliases and deliberate preference proposals, without passive editor monitoring or a general autonomous agent.

**Done when:** only approved rules persist locally, changes take effect through the shared personalization engine, users can inspect/edit/undo/delete/disable them, forgotten rules stay forgotten, and an evaluation shows fewer repeated mistakes without extra semantic errors.

- [ ] Design it (spec): `/architect approved local correction learning`

Current foundations: `engine/personalization.py`, `engine/preference_learning.py`, `engine/context_processor.py`, `ui/dictionary_view.py`, and `ui/companion_studio.py`. This enhancement follows the core device, delivery, and real speech evaluation work. See section 16.5 of the complete Gemini handoff for the existing versus proposed boundary.

### 30. Optional local text repair and infilling · in-progress (sandbox) · needs a decision · GA

Evaluate whether an isolated, quantized small language model (e.g. Qwen2.5-0.5B-Instruct in 4-bit GGUF via llama-cpp-python or onnxruntime-genai) can perform bounded sentence repair, punctuation restoration, disfluency removal, and backtracking cleanup on already-transcribed text without cloud egress.

**Strict boundary:** This is a text-generation infilling transform, **not** an acoustic speech recognizer (ASR). It cannot fix raw phonetic or acoustic errors in Indic languages (Hindi, Tamil, Malayalam) or English accents; acoustic accuracy is evaluated separately under Feature 15. The primary runtime baseline is CPU (AVX2/AVX-512); DirectML is exploratory and experimental.

**Done when:**
- Operates strictly within branch feature/local-slm-repair-sandbox without blocking the RC8 pilot intake.
- Enforces a Three-Tier Guard Protocol: Tier 1 slot-locks numbers, dates, negations, and identifiers; Tier 2 performs bounded infilling; Tier 3 executes FactGuard verification. Any altered or missing entity immediately vetoes the repair.
- Execution deadline is <= 400 ms; failures, timeouts, or FactGuard vetoes immediately fall back to raw Whisper output within <= 5 ms.
- P50 latency <= 300 ms on CPU for 30-word utterances.
- Zero entity hallucinations or mutations across the 150-case adversarial corpus.

- [x] Design it (spec): [spec 0004](../specs/0004-local-text-repair-sandbox.md)
- [ ] Implement bounded prototype in sandbox: feature/local-slm-repair-sandbox
- [ ] Benchmark CPU latency, memory delta, and FactGuard veto rate: /test local text repair sandbox

This follows the core pilot intake and runs in branch isolation. No general screenshot collection, workspace scanning, or cloud egress is permitted. Raw Whisper dictation remains the primary path.

### 22. Safe editing beyond the scratchpad · planned · needs a decision

Explore user requested commands such as replace, remove, append, and undo in external editors only when the target and selection can be read and rechecked safely.

**Done when:** a supported editor has a preview, explicit apply, revision guard, undo or recovery path, and refusal in password fields, terminals, and ambiguous targets. Unsupported apps remain dictation only with Copy Output available.

- [ ] Design it (spec): `/architect safe external voice editing`
