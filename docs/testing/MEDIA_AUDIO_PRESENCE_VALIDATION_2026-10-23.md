# Media audio presence validation, 23 October 2026

This note covers source after local `b67c9b9` plus the current uncommitted
fixes. It is development evidence for scope feature 27, not an RC2 release
manifest or a claim that a visible video was recognized.

## Defects and fixes

| Finding | Reproduction or evidence | Fix |
|---|---|---|
| A short sound hid the pet immediately after a long quiet period | Deterministic clock and fake samples returned `False, True, False, True`; the last value should be false until sustained again | Reset the established latch when quiet exceeds its 1.5 second grace |
| Audio session reads blocked the Qt visibility tick | Five local direct reads measured 137.56 ms on first call, then 26.68 to 29.31 ms; the tick runs every 350 ms | Query on a background sampler thread and give Qt only the cached boolean; 1,000 local cached reads had a maximum of 0.0685 ms |
| A muted session could still have a nonzero meter peak | Windows exposes session mute separately through `ISimpleAudioVolume::GetMute` | Ignore muted or zero volume sessions before reading their peak; fake COM test covers mute and unmute |
| Media feature reused feature number 25 | `docs/scope/voice.md` already owns 25 for runtime performance | Renumber media hiding as feature 27 in scope and module header |

The [Windows mute API](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-isimpleaudiovolume-getmute) documents the separate session mute state. The [Windows peak meter API](https://learn.microsoft.com/en-us/windows/win32/api/endpointvolume/nn-endpointvolume-iaudiometerinformation) documents peak levels and their limits; a meter reading alone does not prove that a browser is showing video.

## Verification completed

- `python -X utf8 -m pytest -q tests/test_companion_visibility.py`: 22 passed. These tests use fake audio samples and COM objects; they do not prove live playback behavior.
- `python -X utf8 tests/run_all_tests.py` with `GITHUB_ACTIONS=true`, `FLOWPILOT_HEADLESS=1`, and `FLOWPILOT_TEST_EXE` pointing at the fresh isolated binary: 54 suites, 49 passed, 5 skipped, 0 failed in 98.83 seconds. The skipped suites include physical focus and insertion work; this is not the strict `--require-all` release gate.
- `npm test`: Node.js and local FastAPI static, REST, and WebSocket checks passed on loopback port 8766.
- `QT_QPA_PLATFORM=offscreen python -X utf8 scratch/ui_audit_20261023.py`: all ten main pages opened; safe Home, Text edits, Dictionary, Scratchpad, Meetings, Insights, Snippets, History, Studio, and Settings actions completed in an isolated profile. Closed Settings and Studio combo values stayed fixed under wheel events. Home scrolled. This was an offscreen interaction audit, not a physical monitor review.
- Fresh isolated PyInstaller build at `scratch/codex-media-validation-20261023/dist/FlowPilot/FlowPilot.exe`: 24,882,896 bytes, SHA-256 `99A7AE9631AD55574EA4DB5FA91B4C7F6211452F0440311CED2B1A866D2F5FA8`. The unpacked folder is 1,111,643,112 bytes across 1,203 files, including the base and small models. This is a validation build; the existing RC2 archive and the user's running application were not replaced.
- Standalone smoke against that exact binary passed: bundled base weights and Silero assets found, mutex held, duplicate instance exited, primary shut down cleanly.
- `FlowPilot.exe --self-test` against the same binary exited 0 with `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and an empty `HF_HOME`. It loaded bundled base weights and transcribed the SAPI fixture. The isolated cache directory remained absent. This is offline model resolution evidence, not a whole system packet capture.

## Still open

- Human desktop checks for audible and muted browser video, background music, a real PowerPoint presentation, Chrome F11, F9 while hidden, app rules, focus integrity, and multi-monitor restore. The feature cannot be promoted from fake audio or offscreen Qt tests.
- The offscreen UI audit still flags narrow button text on some older pages at 880 × 580. Scrolling and action dispatch worked, but real Windows font rendering and visual fit have not been signed off. This visual polish was left outside the media fix.
- Windowed media is approximated by any audible playback. This may hide the pet while music plays and will miss a muted windowed video. Scope feature 24 remains closed on explicit per app rules for that case.
- The current built executable is an isolated developer artifact. A public release needs an interactive gate, a new CI build, and a new manifest. RC2 hashes are historical.
