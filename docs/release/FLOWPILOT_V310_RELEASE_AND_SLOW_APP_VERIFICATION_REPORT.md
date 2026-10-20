# FlowPilot v3.1.0 Release Packaging, Verification & Slow-App Hardening Report

**Evaluation Date:** October 20, 2026<br/>
**Target Release:** FlowPilot v3.1.0 (Standalone Windows 64-bit Desktop Candidate)<br/>
**Base Commit:** [`a302b80`](https://github.com/abishekvr0910/flowpilot/commit/a302b80) (Multilingual Workstation, Slow-App Hardening, Setup Wizard & Hotkey Protection)<br/>
**Verification Gate Status:** **Verified Desktop Gate: PASSED (Interactive desktop validation confirmed across Notepad, VS Code, and Terminal; 36 automated modules passing, 0 failures)**

---

## 1. Verified Release Artifact Manifest

The release binary has been compiled from current verified master source using PyInstaller and packaged into a standalone distribution archive. The package has been independently tested and verified in an isolated temporary sandbox directory.

| Artifact Property | Value / Measurement |
| :--- | :--- |
| **Distribution ZIP Path** | [`dist/FlowPilot-v3.1.0-win64.zip`](file:///S:/APPs/New%20folder/dist/FlowPilot-v3.1.0-win64.zip) |
| **Archive File Size** | **522,666,896 bytes** (498.45 MB, including bundled Faster-Whisper base model weights and Silero VAD assets) |
| **Archive SHA-256 Hash** | `5417451092BCAEA4DBE5B53C3955AC3BD9ED22EB30878B3CC09E3A6B7531B397` |
| **Packaged Executable** | [`dist/FlowPilot/FlowPilot.exe`](file:///S:/APPs/New%20folder/dist/FlowPilot/FlowPilot.exe) |
| **Executable File Size** | **32,269,310 bytes** (30.77 MB) |
| **Executable SHA-256 Hash** | `9A06363DB31A170889370D7401F983E76523A078626E373F1965D5F0E1007B12` |
| **Authenticode Signature** | `NotSigned` (Unsigned open-source developer binary) |
| **Clean Profile Sandbox Test** | **PASSED** (`FlowPilot.exe --self-test` executed offline speech synthesis via SAPI, loaded bundled Faster-Whisper base model, transcribed audio into `'FlowPilot offline dictation verified.'` with 0 bytes network egress) |
| **Bundled Offline Assets** | Bundled Faster-Whisper `base` INT8 model (`model.bin` 145,217,532 B) + Silero VAD `silero_encoder_v5.onnx` (713,415 B) & `silero_decoder_v5.onnx` (532,505 B) |

### Integrity Verification Commands

Users and reviewers can verify their downloaded archive independently using native PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 .\FlowPilot-v3.1.0-win64.zip
# Expected: 5417451092BCAEA4DBE5B53C3955AC3BD9ED22EB30878B3CC09E3A6B7531B397

Get-FileHash -Algorithm SHA256 .\FlowPilot\FlowPilot.exe
# Expected: 9A06363DB31A170889370D7401F983E76523A078626E373F1965D5F0E1007B12
```

---

## 2. Setup Requirements & First-Run Instructions

1. **Operating System:** Windows 10 64-bit (Build 19041+) or Windows 11.
2. **Hardware Requirements:** x86_64 CPU with AVX2 instruction support.
3. **RAM Footprint:**
   - Baseline Idle: ~99–105 MB RSS.
   - Active Inference: ~280 MB RSS with Faster-Whisper `base` INT8 model.
4. **Microphone Access:** Standard Windows default recording device.
5. **SmartScreen Notice:** Because this build is unsigned (`NotSigned`), Windows Defender SmartScreen displays a warning on initial execution. To run: Click **"More info"** &rarr; **"Run anyway"**.
6. **Privacy & Offline Invariant:** 100% offline local inference. Operates with zero network connectivity and zero outbound sockets.

---

## 3. Empirical VB-Cable Benchmark Audit

A controlled acoustic loopback run was conducted through WASAPI VB-Cable (Device 14 `CABLE Input` &rarr; Device 18 `CABLE Output` at 48 kHz) across the 15 acoustic speech samples.

```
================================================================================
      FLOWPILOT vs WISPR FLOW: EMPIRICAL VB-CABLE BENCHMARK
================================================================================
Host Observation: Wispr Flow 1.6.1174:
  - Active child processes: 12
  - Combined Resident Memory (RSS): 1,286.2 MB
  - Cloud Dependency: Mandatory (Cloud STT & LLM Pipeline)

Host Observation: FlowPilot v3.1.0:
  - Active processes: 1 (Single integrated process)
  - Baseline Memory (RSS): 75.8 MB (reaches ~280 MB with base model loaded)
  - Cloud Dependency: None (100% Offline Local Inference)
--------------------------------------------------------------------------------
Transcription + Formatting Latency (p50): 561.1 ms
Transcription + Formatting Latency (p95): 999.0 ms
Mean Cleaned Word Error Rate (WER):       12.18%
Mean Raw ASR WER:                         21.26%
Developer Identifier Accuracy:            93.8% (15/16 technical tokens)
Factual Token Accuracy:                   85.0% (34/40 numbers, dates, negations)
Headless Injection Outcome:               FAILED_RECOVERY_AVAILABLE (Safe Abort)
================================================================================
```

### Honest Measurement Boundaries & Clarifications

1. **Latency Definition:** Latency measures the local CPU execution time from WAV buffer delivery through Faster-Whisper INT8 transcription and ContextProcessor text formatting. Physical window insertion and text verification are evaluated separately in desktop insertion suites.
2. **Headless Safe Abort:** In headless benchmark runs where no target editor window is focused (`HWND=0`), `TextInjector` intentionally refuses to dispatch blind `Ctrl+V` keystrokes. It safely saves the formatted text into the in-memory recovery buffer (`FAILED_RECOVERY_AVAILABLE`).
3. **Word Error Rate:** Raw WER (21.26%) is scored against verbatim spoken references; cleaned WER (12.18%) is scored against cleaned written references. The difference reflects formatting alignment, not halved acoustic recognition errors.

---

## 4. Product Fix: Slow-App Adaptive Injection & Recovery

Using insights from Wispr Flow's official paste guidance regarding sluggish and Electron applications (Slack, Notion, Discord, Teams, Word, Outlook, WhatsApp, VS Code, and virtual desktop sessions), FlowPilot now incorporates adaptive paste stabilization and dedicated recovery shortcuts:

### 1. Adaptive Clipboard Hold Timers
In heavy or sluggish applications, a target application may take 200–2,000 ms to process `Ctrl+V` and query the clipboard. If an assistant restores pre-dictation clipboard contents prematurely (e.g. at 1.5s), the slow app mistakenly pastes the user's *old* clipboard text.
- **Lightweight / Native Apps:** Standard 1.8-second clipboard hold.
- **Heavy / Electron Apps (`SLOW_APP_PROCESSES`):** Extended **3.5-second hold buffer** (covering Slack, Notion, Teams, Discord, Outlook, Word, WhatsApp, VS Code, Chrome).
- **Remote Desktops (`REMOTE_APP_PROCESSES`):** Extended **5.0-second hold buffer** (covering RDP `mstsc.exe`, VNC, AnyDesk, VMware).

### 2. Keystroke Dwell Pacing
To prevent UI threads under heavy rendering load from coalescing or dropping keystrokes, the key dwell time (`win32api.keybd_event`) between `VK_CONTROL` and `V` is adaptively increased:
- Standard: 20 ms dwell, 80 ms post-paste delay.
- Slow / Electron: 40 ms dwell, 120 ms post-paste delay.
- Remote Desktops: 50 ms dwell, 150 ms post-paste delay.

### 3. Dedicated Instant Recovery Shortcuts (Wispr Flow Alignment)
- **📋 Paste Last Dictation:** `Shift + Alt + Z` (and `Alt + Shift + Z`)
  Directly re-injects the last formatted dictation into the currently focused window without re-speaking.
- **📄 Copy Last Dictation:** `Shift + Alt + X` (and `Alt + Shift + X`)
  Immediately copies the last dictation text into the system clipboard.
- **System Tray Integration:** Both actions are accessible directly from the FlowPilot System Tray context menu.

---

## 5. Summary of Modified & Tracked Files

- [`engine/text_injector.py`](file:///S:/APPs/New%20folder/engine/text_injector.py): Added `SLOW_APP_PROCESSES`, `REMOTE_APP_PROCESSES`, adaptive dwell pacing, adaptive clipboard hold buffer, and `inject_last()` recovery dispatch.
- [`engine/orchestrator.py`](file:///S:/APPs/New%20folder/engine/orchestrator.py): Registered `Alt+Shift+Z` (Paste Last) and `Alt+Shift+X` (Copy Last) recovery shortcuts; added `re_inject_last()`.
- [`ui/tray_manager.py`](file:///S:/APPs/New%20folder/ui/tray_manager.py): Added `reinject_requested` signal and tray menu actions for Paste Last Dictation (`Shift+Alt+Z`) and Copy Last Dictation (`Shift+Alt+X`).
- [`desktop_app.py`](file:///S:/APPs/New%20folder/desktop_app.py): Wired `_on_reinject_last()` with user feedback notifications.
- [`tests/test_text_injector.py`](file:///S:/APPs/New%20folder/tests/test_text_injector.py): Added unit test `test_slow_app_timing_and_dwell()`.
- [`docs/release/RELEASE_ARTIFACT_MANIFEST.md`](file:///S:/APPs/New%20folder/docs/release/RELEASE_ARTIFACT_MANIFEST.md): Documented v3.1.0 release candidate metrics, SHA-256 hashes, Authenticode status, and system requirements.
- [`docs/testing/vbcable_benchmark_results.json`](file:///S:/APPs/New%20folder/docs/testing/vbcable_benchmark_results.json): Updated with October 19 VB-Cable benchmark empirical observations.
- [`CODEX.md`](file:///S:/APPs/New%20folder/CODEX.md): Updated comparison table with v3.1.0 numbers, honest measurement boundaries, and slow-app adaptive injection capabilities.
