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

**Done when:** backend and UI refuse external mutation, forged transaction labels cannot bypass the restriction, and scratchpad revision checks and undo still pass regression tests. This is a source repair, not a new packaged release.

- [x] Implement the bounded repair: `/develop external transform safety`
- [x] Verify backend refusal and Qt control behavior: `/check verify external transform safety`
- [x] Protect dispatch, status, recovery, and scratchpad behavior: `/test external transform safety`

Plan: [remediation directive](../design/GEMINI_SCOPE_AND_RELEASE_REMEDIATION.md). Code in `engine/transforms_engine.py`, `ui/transforms_view.py`, and `tests/test_honest_transforms.py`.

### 15. Real speaker language evaluation · planned · needs a decision

Measure speech from consenting native speakers in English, Hindi, Tamil, and Malayalam, including mixed language and developer terms. Keep synthetic speech in a separate diagnostic group.

**Done when:** each advertised language has a published sample count, corpus rules, word and character error results, critical fact errors, hardware, model, and failure examples. Do not promote an experimental language from synthetic tests alone.

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

### 22. Safe editing beyond the scratchpad · planned · needs a decision

Explore user requested commands such as replace, remove, append, and undo in external editors only when the target and selection can be read and rechecked safely.

**Done when:** a supported editor has a preview, explicit apply, revision guard, undo or recovery path, and refusal in password fields, terminals, and ambiguous targets. Unsupported apps remain dictation only with Copy Output available.

- [ ] Design it (spec): `/architect safe external voice editing`
