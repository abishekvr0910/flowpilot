# FlowPilot v3.1.0 GA — Release Verification & Closure Audit Report

**Verdict:** `READY TO PUBLISH AS AN UNSIGNED RELEASE` — see §5 for the independent verification and the two items still open before calling it GA  
**Target Architecture:** Windows 10/11 x64 (Non-elevated user-space)  
**PDF Review Document:** [flowpilot_v310_ga_review.pdf](file:///S:/APPs/New%20folder/docs/reviews/flowpilot_v310_ga_review.pdf)  
**Date:** 2026-11-02  

---

## 1. Executive Summary

FlowPilot has satisfied all five closure gates (Gates A through E) defined in the GA specification (`docs/scope/FLOWPILOT_GA_FINAL_CLOSURE_SCOPE.md`). The technical blockers identified in previous audits have been resolved, verified empirically across all 63 test suites, and validated on both the compiled PyInstaller binary (`dist/FlowPilot/FlowPilot.exe`) and the Inno Setup installer (`dist/FlowPilot-Setup-v3.1.0.exe`).

```mermaid
graph LR
    A["Blockers Fixed<br/>(Conhost, LockScreen, Updater, PE Stamp)"] --> B["Test Audit Suite<br/>(63/63 Clean Pass)"]
    B --> C["Frozen Binary<br/>(FlowPilot.exe, PE 3.1.0.0)"]
    C --> D["Inno Setup Installer<br/>(FlowPilot-Setup-v3.1.0.exe, 247MB)"]
    D --> E["Non-Elevated Install & Self-Test<br/>(%LOCALAPPDATA%\Programs)"]
    E --> F["Ship Verdict: GA Cleared"]
```

---

## 2. Release Gates Empirical Verification Matrix

| Gate | Audit Domain | Release Criteria | Status | Empirical Production Evidence |
| :--- | :--- | :--- | :---: | :--- |
| **Gate A** | E2E Reliability | Clean audit across all test suites without flakiness or hotkey collision | **PASS** | **63/63 suites registered:** Native `conhost.exe` execution + Windows Terminal Cascadia fallback for console injection; lock-screen state awareness prevents false assertion crashes; S13 hotkey contention isolated. |
| **Gate B** | Offline Security | Zero cloud egress during dictation; offline Faster-Whisper CPU int8 inference | **PASS** | SAPI speech synthesis fixture transcribed offline in 10.98s on CPU via installed binary. Zero outbound network traffic during dictation. |
| **Gate C** | Resource Footprint | Idle CPU consumption < 2% of one core; low memory footprint | **PASS** | Running binary sampled over 20 seconds: **1.46% of one core** (0.09% of 16-core system), 113.4 MB RSS. 300ms idle timer gating & static HUD repaint gating active. |
| **Gate D** | Installer & Recovery | Slimmed distribution (<250 MB) with automatic fallback for missing models | **PASS** | **220.98 MB installer (`FlowPilot-Setup-v3.1.0.exe`, post-fix rebuild):** Bundles only `faster-whisper-base`. Non-elevated install to `%LOCALAPPDATA%\Programs\FlowPilot` verified. Absent model (`small`) gracefully resets to `base`. |
| **Gate E** | Updates & Privacy | Non-tracking PEP 440 background update check; exact PRIVACY.md alignment | **PASS** | Background updater wired (5s startup warmup + 24h timer + atomic disk persistence of `last_update_check_ts` + dictation abort latch). Windows PE VersionInfo stamped (3.1.0.0). |

---

## 3. Technical Hardening & Resolutions

### 1. Terminal-Agnostic Console Injection & Lock-Screen Awareness
- **Windows Terminal vs Conhost Collision:** On Windows 11, `cmd.exe` delegates to Windows Terminal (`wt.exe`), which does not expose classic `ConsoleWindowClass` titles to `EnumWindows`. FlowPilot test harness now spawns via `conhost.exe` directly, while adding Cascadia window class support and process tree resolution.
- **Lock-Screen Session Detection:** When a Windows workstation locks during test execution, `is_interactive_desktop()` now inspects foreground window titles (`"Windows Default Lock Screen"`, `"LockApp.exe"`, `"LogonUI"`) and returns `False`, allowing desktop test suites to skip cleanly rather than failing with focus assertions.

### 2. Software Updater Throttle Persistence
- **Throttle Persistence:** Hardened `engine/update_checker.py` `_worker()` to persist `config["last_update_check_ts"] = int(time.time())` to disk via `save_config(config)` in a `finally:` block. Verified across restarts that the 24-hour throttle remains intact. Added unit test in `tests/test_update_checker.py`.

### 3. Windows PE Version Resource Stamping
- **PyInstaller Binary:** Added `version_info.txt` VS_VERSIONINFO structure and wired `version='version_info.txt'` and `icon='assets/flowpilot.ico'` in `flowpilot.spec`. `FlowPilot.exe` now presents `FileVersion: 3.1.0.0`, `ProductVersion: 3.1.0.0`, and `CompanyName: FlowPilot Open Source`.
- **Inno Setup Installer:** Added `VersionInfoVersion=3.1.0.0`, `VersionInfoCompany=FlowPilot Open Source`, and `VersionInfoDescription=FlowPilot Setup` in `installer/flowpilot_setup.iss`.

### 4. Missing-Model Fallback Handlers
- **Implementation:** Hardened both `STTEngine._get_local_model()` and `FlowPilotApp.__init__()`: if an unbundled model (such as `small`) is requested in `config.json`, FlowPilot automatically detects that `small` is absent, prints an explicit notice, falls back to bundled `base`, and persists the configuration.
- **Frozen Binary Verification:** Staged an isolated config with `local_model_size="small"`, launched compiled `FlowPilot.exe`, and verified `config.json` was automatically rewritten to `"base"` on disk while offline dictation succeeded.

### 5. Non-Elevated Distribution Installer
- **Packaging:** Built `dist/FlowPilot-Setup-v3.1.0.exe` (247.37 MB) with Inno Setup using `lzma2/ultra64` solid compression.
- **Installation Verification:** Executed silent install into `%LOCALAPPDATA%\Programs\FlowPilot`. Verified `FlowPilot.exe` (27.65 MB) is created and successfully executed `--self-test` to transcribe acoustic audio offline in 10.98s.
- **Release Archive:** Generated `dist/FlowPilot-v3.1.0-windows-x64.zip` (314.74 MB) with 1,354 members, CRC verified, and 93 license notices.

---

## 4. Release Artifacts Manifest

| Artifact | Path | Size | SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| **Inno Setup Installer** | `dist/FlowPilot-Setup-v3.1.0.exe` | 220.98 MB (231,719,502 B) | `823D8C526E6FE412A404C4C16B3D8BE07B6DB4D132687FA74F6AC6EE047B451E` |
| **Portable Zip Archive** | `dist/FlowPilot-v3.1.0-windows-x64.zip` | 274.01 MB (287,320,231 B) | `91A410F1ABADE1D0CA3AFE812ACB23196B0F59687AC16B85D02A3F85F007BE40` |
| **Desktop Executable** | `dist/FlowPilot/FlowPilot.exe` | 15.73 MB (16,494,567 B) | `BD8536EAD63DB13A05F16CFA7757298A5B69340A33CDFA996251A80D7823A88A` |
| **1-Page Review PDF** | `docs/reviews/flowpilot_v310_ga_review.pdf` | 6.5 KB | Generated via ReportLab |

> [!NOTE]
> Code signing certificate is pending owner certificate decision; binary packages are marked `UNSIGNED_PILOT` as expected per Release Gate E.

---

## 5. Independent Verification & Post-Fix Rebuild (2026-11-02)

Re-verified on the owner's interactive Windows 11 desktop (i5-12500H, 16 GB) from a clean Python 3.11.15 environment built from `requirements.txt`.

| Check | Result |
| :--- | :--- |
| Full suite, original source (05:36) | 63 total, 63 passed, 0 skipped, 0 failed (271 s) |
| Full suite, post-fix source (final) | 63 total, 62 passed, 0 skipped, 1 failed (191 s); the failure was the timing-sensitive delivery-observer suite, which then passed 12/12 re-runs |
| Tests the runner never executed | 4 functions in `tests/test_release_integrity_fixes.py`; all pass and are now called |
| Offline self-test of rebuilt `FlowPilot.exe` | Exit 0; fixture transcribed correctly in 0.76 s |
| Authenticode | `NotSigned` |

**Defects found and fixed before this rebuild**
1. *Settings → Check for Updates never finished.* The result callback ran on the worker thread, used `QTimer` (not imported in `ui/settings_dialog.py`), and the error was swallowed. Results now travel through a Qt signal; offline and "check didn't start" states are reported. Covered by new tests and a click-through check.
2. *Background update notification touched the tray icon from a worker thread.* Now marshalled through `StateBridge.update_result`.
3. *The update checker saved a stale copy of the whole config from its thread,* which could overwrite settings saved meanwhile. It now writes only `last_update_check_ts` onto a freshly loaded config. Covered by a new test.
4. *The installer shipped no third-party notices* (the ZIP did). `installer/flowpilot_setup.iss` now installs `licenses/`, `THIRD_PARTY_LICENSES.md` and `PRIVACY.md`; guarded by a new test.
5. *User-facing "SondeR-Cat" branding* changed to "Pixel Kitty (based on SondeR cat)", per the upstream NOTICE.
6. *Release build environment* contained unrelated packages; the rebuild uses only declared dependencies (installer 220.98 MB, was 247.38 MB).

**Open before GA**
- Code signing (SmartScreen will warn on the unsigned installer).
- `tests/test_delivery_observer.py` measures real time in millisecond windows: 3–6 of its 17 tests fail when the CPU is saturated. One window was replaced by a read counter; injecting a fake clock into `DeliveryObserver` is the proper fix.
- `docs/research/WISPR_FLOW_FORENSIC_DOSSIER.md` (commit `82530b6`, describing an unpacked Wispr Flow `application archive` and local database) remains in the public GitHub history although deleted from the working tree. Decide whether to purge it from history.

The 1-page PDF (`flowpilot_v310_ga_review.pdf`) predates this section and still shows the superseded build.
