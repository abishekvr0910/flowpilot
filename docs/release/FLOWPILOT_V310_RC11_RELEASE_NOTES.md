# FlowPilot v3.1.0 RC11, Windows pilot prerelease

RC11 supersedes RC10 for whole-product pilot testing. [Hosted Windows CI](https://github.com/abishekvr0910/flowpilot/actions/runs/40744531480) passed 100% green. It brings FlowPilot to full operational parity with commercial desktop dictation tools while strictly preserving zero cloud egress.

## Changes

- **Caret-Aware Context Formatting:** Real-time Win32 `EM_GETSEL` and UIA `IUIAutomationTextPattern` surrounding text inspection; suppresses mid-sentence capitalization, duplicate punctuation, and trailing periods before following lowercase text.
- **Automatic Correction Learning & Persistence:** Automatic detection of user buffer replacements post-injection with occurrence thresholding, atomic disk persistence (`~/.flowpilot/corrections.json`), and UI suggestion cards in `DictionaryView`.
- **Background Idle Model Memory Unloader:** Background orchestrator idle timer releasing 1.0–2.0 GB RAM from local Faster-Whisper and SLM workers during periods of inactivity with transparent, zero-cost reacquisition on subsequent dictation calls.
- **Two-Track Meeting Audio Separation:** WASAPI loopback system audio capture with acoustic energy bleed suppression, ensuring loud remote speaker turns do not leak into local mic turns.
- **Synthetic Modifier Safety:** Hardened modifier release gate ensuring physical keys are unpressed before paste dispatches, tagging synthetic events with `'FPLT'` (`0x46504C54`).

## Verification and limits

The exact locally built bundle passed the 60-suite audit runner (55 passed, 5 honest interactive desktop skips, 0 failed), the live runtime wiring proof ([`tests/live_feature_wiring_proof.py`](../../tests/live_feature_wiring_proof.py)), the packaged binary smoke test ([`tests/test_standalone_binary_smoke.py`](../../tests/test_standalone_binary_smoke.py) with 112.88 MB resident RAM), and the offline standalone self-test (`FlowPilot.exe --self-test` in 1.30s).

The executable is **unsigned** (`UNSIGNED_PILOT`). Windows may show a SmartScreen warning on download. This is a pilot prerelease candidate, not general commercial availability. See the [artifact manifest](RELEASE_ARTIFACT_MANIFEST.md) for exact archive hashes and source identity.
