# Published & Candidate Release Manifest

**Last updated:** 2026-10-19. This manifest documents official release binaries and verified distribution candidate archives.

## 1. Candidate Release: FlowPilot v3.1.0 (Windows x64)

Built from master (`ecb3a97` + multilingual workstation & slow-app adaptive pacing updates). Tested on an isolated clean profile.

| Field | FlowPilot v3.1.0 Distribution Candidate |
|---|---|
| Release Version | `v3.1.0` (Workstation & Multilingual Intelligence) |
| Base Commit | `ecb3a97` + multilingual, user-facing fixes & slow-app upgrades |
| Distribution Archive | `dist/FlowPilot-v3.1.0-win64.zip` |
| Archive Size | **522,666,896 bytes** (498.45 MB, including bundled Faster-Whisper base model weights and Silero VAD assets) |
| Archive SHA-256 | `5417451092BCAEA4DBE5B53C3955AC3BD9ED22EB30878B3CC09E3A6B7531B397` |
| Executable File | `dist/FlowPilot/FlowPilot.exe` |
| Executable Size | **32,269,310 bytes** (30.77 MB) |
| Executable SHA-256 | `9A06363DB31A170889370D7401F983E76523A078626E373F1965D5F0E1007B12` |
| Bundled Model Weights | Faster-Whisper `base` (`models/faster-whisper-base/model.bin`, 145.2 MB) + Silero VAD v5 ONNX assets |
| Authenticode Status | `NotSigned` (Unsigned developer build. Standard or EV code signing establishes identity to build SmartScreen reputation over time, but does not provide immediate suppression.) |
| Standalone Offline Self-Test | **PASSED** (`FlowPilot.exe --self-test` executed offline speech synthesis via SAPI, loaded bundled Faster-Whisper base model, transcribed audio into `'FlowPilot offline dictation verified.'` with 0 bytes network egress) |
| Desktop Gate Status | **PASSED** (Interactive desktop validation confirmed across Notepad, VS Code, and Terminal; 36 automated modules passing with 0 failures) |

### Independent Integrity Verification

Verify your downloaded ZIP before extraction:

```powershell
Get-FileHash -Algorithm SHA256 .\FlowPilot-v3.1.0-win64.zip
# Expected: 5417451092BCAEA4DBE5B53C3955AC3BD9ED22EB30878B3CC09E3A6B7531B397

Get-FileHash -Algorithm SHA256 .\FlowPilot\FlowPilot.exe
# Expected: 9A06363DB31A170889370D7401F983E76523A078626E373F1965D5F0E1007B12
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
