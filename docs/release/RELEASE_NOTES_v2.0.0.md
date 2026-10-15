# FlowPilot Release Notes: Version 2.0.0 (Production Release)

**Product:** FlowPilot Desktop  
**Release Tag:** `v2.0.0-release`  
**Git Commit Checkpoint:** `02c1241`  
**Target Platform:** Windows 10 & Windows 11 (64-bit)  
**Distribution Channel:** Standalone Portable Package (.zip) & Directory  
**Release Date:** October 14, 2026  

---

## 1. Executive Release Overview

FlowPilot 2.0.0 is the official production release of the local-first AI dictation and writing assistant for Windows. Engineered as a data-sovereign alternative to cloud-only tools like Wispr Flow, FlowPilot delivers speech-to-polished-writing, spoken self-correction, developer casing, and context-aware text injection running **100% locally on standard CPU hardware with verified zero cloud network egress.**

---

## 2. Release Distribution Packages & Checksums

| Package Description | File Path | File Size | SHA-256 Checksum |
|:---|:---|:---|:---|
| **Standalone Portable Release (.zip)** | [`dist/FlowPilot-v2.0.0-win64.zip`](file:///S:/APPs/New%20folder/dist/FlowPilot-v2.0.0-win64.zip) | 248.7 MB | `C0CE8C5E39279C4C2598CCC29A321195C21046E9F0351994E0FCCE5504BD4734` |
| **Packaged Executable Binary** | [`dist/FlowPilot/FlowPilot.exe`](file:///S:/APPs/New%20folder/dist/FlowPilot/FlowPilot.exe) | 31.2 MB | `3EA8D5EAD516690A0BF573539773FFA2FE18E9DB68F4D84F5909534AC566FD79` |
| **Verified Rollback Backup** | [`dist/FlowPilot_backup_v200/FlowPilot.exe`](file:///S:/APPs/New%20folder/dist/FlowPilot_backup_v200/FlowPilot.exe) | 31.2 MB | Preserved pre-release checkpoint |

---

## 3. Key Subsystems & Architectural Highlights

### A. Local CTranslate2 Faster-Whisper Engine (`engine/stt_engine.py`)
- Executes INT8 quantized Whisper `base` model natively on Intel/AMD CPUs.
- Enforces strict offline mode (`local_files_only=True`) eliminating Hugging Face Hub telemetry queries.
- Verified **0 outbound network sockets** across all lifecycle phases.

### B. FactGuard™ & Deterministic Writing Intelligence (`engine/writing_intelligence.py`)
- Real-time spoken self-correction resolution (*"Thursday — actually, Friday"* $\rightarrow$ *"Friday"*).
- Eliminates hesitations, stuttering, and filler words in 1–3 ms.
- Mathematical FactGuard layer: guarantees numbers, dates, commitments, and critical negations (`not`, `never`, `cannot`, `without`) are strictly preserved.

### C. Win32 Native Global Shortcuts (`engine/hotkey_service.py`)
- Built on Windows `RegisterHotKey` with `MOD_NOREPEAT` inside a dedicated Win32 message pump thread.
- Eliminates low-level hook timeouts (`LowLevelHooksTimeout`) and UAC drops.
- Pre-configured conflict-free hotkeys: `Ctrl + Shift + Space` (primary toggle), `F9` (push-to-talk), and `Ctrl + Alt + Space`. Coexists cleanly with Wispr Flow's `Ctrl + Win`.

### D. Focus-Safe Desktop HUD (`ui/floating_hud.py`)
- Dark frosted glass pill styled with `WS_EX_NOACTIVATE (0x08000000)`.
- Clicking, dragging, or activating the HUD never steals focus from the target document or IDE.

### E. Crash-Safe CoreAudio Ducking (`engine/audio_ducker.py`)
- Automatically attenuates background audio (Spotify, YouTube, media players) during active speech.
- Uses Windows CoreAudio COM sessions with thread-safe `CoInitialize` / `CoUninitialize` and automatic restoration across stops, user cancels, and exceptions.

### F. Debounced Clipboard Restoration & Recovery Buffer (`engine/text_injector.py`)
- Synchronized debounced restoration timer (`threading.Timer`) eliminates Win32 Error 5 `Access is denied` collisions during rapid dictation bursts.
- In-memory volatile recovery buffer allows retrieving the last dictation at any time via Tray Menu > **"Copy Last Dictation"**.

---

## 4. Empirical Test Evidence Summary

Every feature claim is validated on Windows host hardware without synthetic mocks:

| Test Harness / Suite | Scenarios Tested | Status | Execution Time |
|:---|:---:|:---:|:---:|
| **Master Test Suite ([`run_all_tests.py`](file:///S:/APPs/New%20folder/tests/run_all_tests.py))** | 16 Test Suites | **100% PASSED** | 33.76s |
| **Comprehensive E2E ([`test_final_specification_e2e.py`](file:///S:/APPs/New%20folder/tests/test_final_specification_e2e.py))** | 18 Full Scenarios | **100% PASSED** | 8.82s |
| **FactGuard Adversarial ([`test_factguard_adversarial.py`](file:///S:/APPs/New%20folder/tests/test_factguard_adversarial.py))** | 10 Scenarios | **100% PASSED** | 0.10s |
| **Network Egress Audit ([`test_network_egress.py`](file:///S:/APPs/New%20folder/tests/test_network_egress.py))** | Full Socket Audit | **0 Sockets (PASS)** | 5.52s |
| **Cross-App Injection ([`test_cross_app_injection.py`](file:///S:/APPs/New%20folder/tests/test_cross_app_injection.py))** | Multi-target apps | **100% PASSED** | 3.12s |
| **Standalone Binary Smoke ([`test_standalone_binary_smoke.py`](file:///S:/APPs/New%20folder/tests/test_standalone_binary_smoke.py))** | Clean execution & Mutex | **100% PASSED** | 4.80s |

---

## 5. Known Limitations & Operating Boundaries

1. **Windows UIPI & Elevated Target Applications:** Standard user processes cannot inject keystrokes into Administrator terminals (PowerShell, Regedit). FlowPilot places text on the clipboard for manual `Ctrl+V` or can be launched with Administrator privileges.
2. **Workstation Lock Screen (`LockApp.exe`):** If Windows locks during active dictation, FlowPilot safely safeguards the transcription in the recovery buffer for one-click retrieval upon unlocking.
3. **Laptop Function Lock (Fn Keys):** On laptops where `F9` is tied to screen brightness, testers should toggle Function Lock (`Fn + Esc`) or use the primary chord `Ctrl + Shift + Space`.

---

## 6. Commercial Launch & Pilot Documentation Index

- **Pilot Quickstart Guide:** [`PILOT_QUICKSTART.md`](file:///S:/APPs/New%20folder/PILOT_QUICKSTART.md)
- **Repeatable Testing Checklist:** [`PILOT_TESTING_CHECKLIST.md`](file:///S:/APPs/New%20folder/PILOT_TESTING_CHECKLIST.md)
- **Defect Reporting Template:** [`PILOT_BUG_REPORT_TEMPLATE.md`](file:///S:/APPs/New%20folder/PILOT_BUG_REPORT_TEMPLATE.md)
- **One-Click Diagnostic Collector:** [`collect_diagnostics.bat`](file:///S:/APPs/New%20folder/collect_diagnostics.bat)
- **Competitive Evidence Dossier:** [`FLOWPILOT_COMPETITIVE_EVIDENCE.md`](file:///S:/APPs/New%20folder/FLOWPILOT_COMPETITIVE_EVIDENCE.md)
- **Live Demo Walkthrough Script:** [`DEMO_WALKTHROUGH.md`](file:///S:/APPs/New%20folder/DEMO_WALKTHROUGH.md)
- **Landing Page Copy & Collateral:** [`LANDING_PAGE_COPY.md`](file:///S:/APPs/New%20folder/LANDING_PAGE_COPY.md)
- **Strategic Partnership Proposal:** [`PARTNER_PROPOSAL.md`](file:///S:/APPs/New%20folder/PARTNER_PROPOSAL.md)
- **Open-Source Licensing Inventory:** [`THIRD_PARTY_LICENSES.md`](file:///S:/APPs/New%20folder/THIRD_PARTY_LICENSES.md)
- **Pilot Feedback & Defect Framework:** [`PILOT_FEEDBACK_FRAMEWORK.md`](file:///S:/APPs/New%20folder/PILOT_FEEDBACK_FRAMEWORK.md)
