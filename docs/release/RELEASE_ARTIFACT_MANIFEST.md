# Published & Candidate Release Manifest

**Last updated:** 2026-10-22 (Reconciled & Packaged). This manifest documents official release binaries and verified distribution archives.

## 1. Distribution Candidate: FlowPilot v3.1.0 (Windows x64)

Built from master with native Sand & Stone Warm Light UI, 3-tab Meetings workspace, and local spoken self-correction intent engine. 100% zero-egress offline inference verified on device.

| Field | FlowPilot v3.1.0 Official Distribution Candidate |
|---|---|
| Release Version | `v3.1.0` (Workstation Refresh, Sand & Stone Design, Spoken Self-Correction Engine & Rights Hardened) |
| Distribution Archive | `dist/FlowPilot-v3.1.0-win64.zip` |
| Archive Size | **772,898,922 bytes** (737.09 MB, includes offline Faster-Whisper `base` + `small` model weights and Silero VAD assets) |
| Archive SHA-256 | `E29D57E2AD1D42FD2B642D60425F37F54346F366D5DD0C0107840684795925EC` |
| Executable File | `FlowPilot/FlowPilot.exe` |
| Executable Size | **24,852,435 bytes** (23.70 MB) |
| Executable SHA-256 | `0CB43E80B30F7C962B94F3AA46B3D92664B9CEC125A434DCBE5FCF8626DCB822` |
| Bundled Model Weights | Faster-Whisper `base` + `small` (`_internal/models/`) + Silero VAD v5 ONNX assets |
| Authenticode Status | `NotSigned` (Unsigned developer build. Standard or EV code signing establishes identity to build SmartScreen reputation over time, but does not provide immediate suppression.) |
| Standalone Offline Smoke Test | **PASSED** (`FlowPilot.exe` smoke test launched with isolated test mutex, validated bundled Silero VAD v5 assets and Faster-Whisper base weights, enforced single-instance mutex, and cleanly terminated with 0 bytes network egress) |
| Offline Transcription Self-Test | **PASSED** (`FlowPilot.exe --self-test` transcribed SAPI fixture on CPU in 3.19s with local correction logic verified offline) |
| Automated Test Gate Status | **51 PASSED, 0 SKIPPED, 0 FAILED** (Registry holds 51 suites. Measured on an interactive Windows 11 desktop: full `run_all_tests.py` verdict "ALL TESTS PASSED" 51/51 in 463.8 s, including the four physical desktop-automation suites. Requires the harness force-foreground fix (`tests/notepad_harness.py::_force_foreground`, AttachThreadInput) for modern Store Notepad 11.2410.21.0. Headless/non-interactive sessions: 46 passed + 4 honest skips.) |

### Reliability & Feature Upgrades in v3.1.0

1. **Native Sand & Stone Warm Light Theme:** Full aesthetic refresh matching modern design standards (`#f5f4f0` warm canvas, 18px rounded white cards, hairline borders, warm amber accents), with Obsidian Dark toggle and dynamic `harmonize_legacy_styles()` for all secondary pages.
2. **Responsive 3-Tab Meetings Workspace:** Refactored Meetings from a cramped 3-column horizontal splitter into 3 clean tabs: **Library**, **Live transcript**, and **Notes & actions**, completely eliminating horizontal clipping at 880×580 minimum window size.
3. **Deterministic Spoken Self-Correction Engine:** Integrated `engine/correction_intent.py` (755 lines) resolving verbal retractions (*"actually"*, *"no wait"*, *"sorry Jane"*, *"I mean"*) before text injection while preserving FactGuard safety invariants.
4. **Competitor Asset & Credential Purge:** Permanently deleted all extracted competitor bundles and credential bridges. Added `.gitignore` defense-in-depth rules; verified zero vendored code in Git history.
5. **Multilingual Honesty:** Withdrew misleading 0.00% synthetic WER claims; established CC0 Mozilla Common Voice real-speech evaluation pipeline (`DE_ES_FR_REAL_VOICE_MANIFEST.json`).
6. **Binary Footprint Optimization:** Trimmed unpacked installation directory by 139 MB (down from 764 MB to 625 MB / 1,199 files); distribution archive size reduced from 388 MB to 326 MB.

### Independent Integrity Verification

Verify your downloaded ZIP before extraction:

```powershell
Get-FileHash -Algorithm SHA256 .\dist\FlowPilot-v3.1.0-win64.zip
# Expected: E29D57E2AD1D42FD2B642D60425F37F54346F366D5DD0C0107840684795925EC

Get-FileHash -Algorithm SHA256 .\dist\FlowPilot\FlowPilot.exe
# Expected: 0CB43E80B30F7C962B94F3AA46B3D92664B9CEC125A434DCBE5FCF8626DCB822
```

### Verification & Compliance Evidence

1. **Artifact Cleanliness Scan:** A full filename and content scan of the unpacked package confirmed **zero** competitor renderers, credential bridges, Electron, Sentry, Supabase, `__pycache__`, or `.pyc` files.
2. **Standalone Smoke Test:** PASSED (`test_standalone_binary_smoke.py`). The executable holds the named single-instance mutex and validates bundled Silero VAD v5 assets and Faster-Whisper base weights.
3. **Offline Transcription Self-Test:** PASSED (`FlowPilot.exe --self-test`). Loaded offline base model on CPU (int8, 8 threads), transcribed fixture audio, and executed local correction logic with zero network egress.
4. **Source Test Suite Gate:** Full regression run across all 51 registered test modules on an interactive Windows 11 desktop: **51 PASSED, 0 SKIPPED, 0 FAILED** (463.8 s). The previous headless-mode gate (46 passed + 4 skips) is superseded: `tests/notepad_harness.py::_force_foreground` makes the four desktop suites pass for real on Win11 modern Notepad.

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
