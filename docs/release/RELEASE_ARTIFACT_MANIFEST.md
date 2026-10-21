# Published & Candidate Release Manifest

**Last updated:** 2026-10-21. This manifest documents official release binaries and verified distribution candidate archives.

## 1. Candidate Release: FlowPilot v3.1.0-RC1 (Windows x64)

Built from master (`9ebee81` + async voice-command worker, microphone release lifecycle, LLM deadline containment, reduced motion frame locking, and pixel import safety). Tested on an isolated clean profile.

| Field | FlowPilot v3.1.0-RC1 Distribution Candidate |
|---|---|
| Release Version | `v3.1.0-RC1` (Release Candidate 1: Workstation, Animation Suite & Hardened Reliability) |
| Base Commit | `007553d` + Async Command Target Matching, Concurrency Slot Integrity & Frame Mapping Fixes |
| Distribution Archive | `dist/FlowPilot-v3.1.0-win64.zip` |
| Archive Size | **388,376,307 bytes** (370.38 MB, including bundled Faster-Whisper base model weights and Silero VAD assets) |
| Archive SHA-256 | `FFFC26EDC20F095D2FA7A61765CB92CFF101523D2B37FC8118A2CBFE771275A6` |
| Executable File | `dist/FlowPilot/FlowPilot.exe` |
| Executable Size | **32,349,213 bytes** (30.85 MB) |
| Executable SHA-256 | `2D0F6B798B232DC5B321A74A03A60004E89C8E2BA0DB2DD73958C5F3A9D060CE` |
| Bundled Model Weights | Faster-Whisper `base` (`models/faster-whisper-base/model.bin`, 145.2 MB) + Silero VAD v5 ONNX assets |
| Authenticode Status | `NotSigned` (Unsigned developer build. Standard or EV code signing establishes identity to build SmartScreen reputation over time, but does not provide immediate suppression.) |
| Standalone Offline Smoke Test | **PASSED** (`FlowPilot.exe` smoke test launched with isolated test mutex, validated bundled Silero VAD v5 assets and Faster-Whisper base weights, enforced single-instance mutex, and cleanly terminated with 0 bytes network egress) |
| Automated Test Gate Status | **48 PASSED, 0 SKIPPED, 0 FAILED** (All 48 test suites fully verified and passing 100%, including all 4 physical desktop UI automation suites: `test_text_injector.py`, `test_notepad_dictation_e2e.py`, `test_cross_app_injection.py`, and `test_final_specification_e2e.py`) |

### Reliability & Verification Fixes in v3.1.0-RC1

1. **Async Voice-Command Target Matching & Selection:** Pass the Scratchpad's exact unique target ID (`_target_id`) and exact selection range (`(start, end)` including collapsed cursor positions like `(6, 6)`) into [`VoiceCommandWorker`](file:///S:/APPs/New%20folder/ui/scratchpad_view.py#L41-L85), ensuring `VoiceEditor.apply_transaction()` verifies target document ownership and selection matches without spuriously raising "Selection changed" or "The target document changed".
2. **Worker Cancellation & Monotonic Request IDs:** Monotonically incrementing `_active_request_id` tracks active commands. Cancel, hide, and close operations mark workers cancelled (`worker.cancel()`); late-arriving or superseded results are rejected, preventing late preview restoration or unwanted Apply button enablement.
3. **Comprehensive LLM Deadline Containment & Concurrency Slot Integrity:** `LocalLLMProvider.is_available()` health checks and `transform()` requests are strictly bounded inside the requested wall-clock deadline (e.g. 50ms). Outstanding requests are bounded (`MAX_CONCURRENT_TRANSFORMS = 1`), with the concurrency slot released strictly when the underlying background execution thread actually finishes, rather than prematurely when the caller times out. Cancel tokens abort background network operations upon timeout, and `shutdown_local_llm()` guarantees clean exit without waiting indefinitely on abandoned background work.
4. **Explicit Animation State Frame Mappings:** Unified explicit state frame mappings (`build_default_frame_mappings`, `resolve_frame_for_state`) in [`engine/companion_assets.py`](file:///S:/APPs/New%20folder/engine/companion_assets.py#L415-L490). 12-frame spritesheets correctly map Frame 0 to Idle, Frames 1..10 to Action/Listening, and Frame 11 to Celebrate, applied consistently across Pixel Creator, Animation Preview, Companion Renderer, and Desktop Floating HUD.
5. **Pixel Creator Import Hardening:** Enforced pre-decode security guards (`MAX_IMPORT_FILE_SIZE = 5MB`, `MAX_IMPORT_DIMENSION = 2048px`), added multi-frame slicing up to 12 frames, and dynamic frame selector button rebuilding.
6. **Command Microphone Lifecycle:** Command audio stream fully terminated (`keep_stream_alive=False`) when Scratchpad is hidden, closed, or edit is cancelled.
7. **Physical Desktop Verification:** All 4 physical desktop automation test suites (`test_text_injector.py`, `test_notepad_dictation_e2e.py`, `test_cross_app_injection.py`, `test_final_specification_e2e.py`) execute their full suites without early skips, confirming real focus handling, recovery buffers, and document insertions.

### Independent Integrity Verification

Verify your downloaded ZIP before extraction:

```powershell
Get-FileHash -Algorithm SHA256 .\FlowPilot-v3.1.0-win64.zip
# Expected: FFFC26EDC20F095D2FA7A61765CB92CFF101523D2B37FC8118A2CBFE771275A6

Get-FileHash -Algorithm SHA256 .\FlowPilot\FlowPilot.exe
# Expected: 2D0F6B798B232DC5B321A74A03A60004E89C8E2BA0DB2DD73958C5F3A9D060CE
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
