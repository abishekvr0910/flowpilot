# Published & Candidate Release Manifest

**Last updated:** 2026-10-21. This manifest documents official release binaries and verified distribution candidate archives.

## 1. Candidate Release: FlowPilot v3.1.0-RC1 (Windows x64)

Built from master (`9ebee81` + async voice-command worker, microphone release lifecycle, LLM deadline containment, reduced motion frame locking, and pixel import safety). Tested on an isolated clean profile.

| Field | FlowPilot v3.1.0-RC1 Distribution Candidate |
|---|---|
| Release Version | `v3.1.0-RC1` (Release Candidate 1: Workstation, Animation Suite & Hardened Reliability) |
| Base Commit | `9ebee81` + Reliability Hardening Patches |
| Distribution Archive | `dist/FlowPilot-v3.1.0-win64.zip` |
| Archive Size | **388,364,445 bytes** (370.37 MB, including bundled Faster-Whisper base model weights and Silero VAD assets) |
| Archive SHA-256 | `EEBF54ED29260F8A8811AD0703FB59057D93B2F7E59C8E9002B2CEE1672FFF97` |
| Executable File | `dist/FlowPilot/FlowPilot.exe` |
| Executable Size | **32,343,257 bytes** (30.84 MB) |
| Executable SHA-256 | `EABFC45BE5A54629828F2C3253B2FB35B0FA5F4523E79AE6854644F7FD8B04F4` |
| Bundled Model Weights | Faster-Whisper `base` (`models/faster-whisper-base/model.bin`, 145.2 MB) + Silero VAD v5 ONNX assets |
| Authenticode Status | `NotSigned` (Unsigned developer build. Standard or EV code signing establishes identity to build SmartScreen reputation over time, but does not provide immediate suppression.) |
| Standalone Offline Smoke Test | **PASSED** (`FlowPilot.exe` smoke test launched with isolated test mutex, validated bundled Silero VAD v5 assets and Faster-Whisper base weights, enforced single-instance mutex, and cleanly terminated with 0 bytes network egress) |
| Automated Test Gate Status | **44 PASSED, 4 SKIPPED** (44 automated test modules passed; 4 physical desktop UI automation suites cleanly skipped in non-interactive/isolated CI session: `test_text_injector.py`, `test_notepad_dictation_e2e.py`, `test_cross_app_injection.py`, `test_final_specification_e2e.py`; 0 test failures) |

### Reliability & Verification Fixes in v3.1.0-RC1

1. **Async Voice-Command Offloading:** Voice-command transcription and LLM edit planning offloaded from Qt main thread to background `VoiceCommandWorker(QThread)` in [`ui/scratchpad_view.py`](file:///S:/APPs/New%20folder/ui/scratchpad_view.py), eliminating UI freeze.
2. **Command Microphone Lifecycle:** Command audio stream fully terminated (`keep_stream_alive=False`) when Scratchpad is hidden, closed, or edit is cancelled.
3. **Strict LLM Wall-Clock Deadline Containment:** `LocalLLMProvider.transform()` enforces strict wall-clock deadline containment via persistent background thread pool (`_TRANSFORM_EXECUTOR`), aborting hanging or slow LLM requests within budget (e.g. 0.3s) and safely falling back without stalling the application.
4. **Reduced Motion & State-Gated Spritesheet Framing:** Spritesheet animations lock strictly to static Frame 0 when `reduced_motion` is enabled, and celebration frames (Frame 2 / last frame) are strictly gated behind verified confirmed/pasted states.
5. **Pixel Creator Import Hardening:** Enforced pre-decode security guards (`MAX_IMPORT_FILE_SIZE = 5MB`, `MAX_IMPORT_DIMENSION = 2048px`), added multi-frame slicing up to 12 frames, and dynamic frame selector button rebuilding.
6. **Character Preset Clarification:** Oneko and Shimeji presets are categorized accurately as visual companion sprite themes, distinct from screen-level cursor chasing or desktop window-climbing behaviors.

### Independent Integrity Verification

Verify your downloaded ZIP before extraction:

```powershell
Get-FileHash -Algorithm SHA256 .\FlowPilot-v3.1.0-win64.zip
# Expected: EEBF54ED29260F8A8811AD0703FB59057D93B2F7E59C8E9002B2CEE1672FFF97

Get-FileHash -Algorithm SHA256 .\FlowPilot\FlowPilot.exe
# Expected: EABFC45BE5A54629828F2C3253B2FB35B0FA5F4523E79AE6854644F7FD8B04F4
```

### System & Setup Requirements

1. **Operating System:** Windows 10 (Build 19041+) or Windows 11 64-bit.
2. **Hardware:** x86_64 CPU with AVX2 support (Intel Core i5/i7/i9 6th gen+, AMD Ryzen 1000+).
3. **RAM:** 8 GB system RAM recommended (FlowPilot utilizes ~100 MB baseline resident RAM, ~280 MB with Faster-Whisper base model loaded).
4. **Microphone:** Standard default Windows recording device (WASAPI / DirectSound).
5. **SmartScreen & Antivirus:** Because this is an unsigned developer build (`NotSigned`), Windows Defender SmartScreen may display an informational prompt on first launch ("Windows protected your PC"). Click **"More info"** -> **"Run anyway"**. Code signing certificates establish identity to accumulate reputation over time, but do not bypass initial reputation thresholds unconditionally.
6. **Network & Privacy Invariant:** 100% offline local inference. Zero outbound sockets or cloud dependencies.

---

## 2. Historical Published Release: FlowPilot v3.0.2

| Field | Published v3.0.2 Windows release |
|---|---|
| Release | [`v3.0.2-release`](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.0.2-release) |
| Source commit | `b9bd76396b2883fa2e87e8b131d231dc39c34515` |
| Download | [`FlowPilot-v3.0.2-win64.zip`](https://github.com/abishekvr0910/flowpilot/releases/download/v3.0.2-release/FlowPilot-v3.0.2-win64.zip) |
| Published asset size | 252,311,634 bytes |
| GitHub asset SHA-256 | `985e031c7af2617e4c03138d1a00472607ff9f9e1d2cff636827f26077f63f74` |
