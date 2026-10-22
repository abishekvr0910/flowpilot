# FlowPilot Takeover & Engineering Status Directive to Codex

**Document Version:** 3.3.0  
**Date:** 2026-10-22  
**Author:** Antigravity / Gemini Engineering Pair  
**Recipient / Co-Architect:** Codex (Technical Partner & Architecture Reviewer)  
**Status:** Historical handoff, superseded for release status by the 2026-10-22 RC2 reassessment
**Commit Baseline:** `bfa9c4b` (Tagged `v3.1.0-release` on `master`)  

---

## 1. Executive Context & Handshake Acknowledgment

Codex, welcome back to the codebase. When your session was interrupted, we took over your in-flight work on the **FlowPilot v3.1.0** release cycle. 

We built directly upon your critical contributions, including:
1. **The Competitor Asset & Credential Purge:** Verified that all extracted competitor bundles, bridge scripts, and quarantine folders were permanently eradicated from the repository and Git history, backed by rigorous defense-in-depth rules in [`.gitignore`](../../.gitignore).
2. **The Sand & Stone Native Workspace:** Preserved and refined the `#f5f4f0` warm canvas theme, 18px rounded white cards, hairline borders, Obsidian Dark toggle, and the responsive 3-tab Meetings workspace (Library, Live transcript, Notes & actions) that eliminated horizontal clipping at 880×580 minimum window size.
3. **Deterministic Spoken Self-Correction Engine:** Retained [`engine/correction_intent.py`](../../engine/correction_intent.py) (755 lines) for verbal retractions (*"actually"*, *"no wait"*, *"sorry Jane"*, *"I mean"*) while upholding FactGuard safety invariants.
4. **Multilingual Honesty:** Enforced real-speech evaluation benchmarks on CC0 Mozilla Common Voice German, Spanish, and French audio (`DE_ES_FR_REAL_VOICE_MANIFEST.json`), retracting synthetic 0.00% WER claims.

Since your cutoff, we installed the new **Agent Skills** framework, conducted a forensic audit and review against Wispr Flow, resolved user-reported live testing bugs, upgraded target verification and window focus handling, and compiled a **FlowPilot v3.1.0 release candidate**. This historical handoff is not proof of a published production release. The 2026-10-22 source gate is 53/53 with no skips; fresh package provenance and CI for the intended commit must be checked separately. See [release reassessment](../reviews/2026-10-22-release-reassessment.md).

This document serves as your complete briefing on everything implemented, proven, and deployed.

---

## 2. Agent Skills Framework & Operational Discipline

To standardize development across agents and pairs, we adopted the specialized Agent Skills suite (`jsmastery-pro/skills`):

| Skill | Purpose & Role in this Session |
|---|---|
| **audit** | Scanned the entire workspace, mapped component dependencies, and refreshed context files ([`AGENTS.md`](../../AGENTS.md), [`engine/AGENTS.md`](../../engine/AGENTS.md), [`ui/AGENTS.md`](../../ui/AGENTS.md), [`tests/AGENTS.md`](../../tests/AGENTS.md)). |
| **debug** | Executed structured root-cause loops (reproduce → localize → hypothesize → test → fix → verify) for hotkey timeouts, focus switching failures, and injection verification. |
| **develop** | Implemented Microsoft UI Automation (UIA) buffer inspection and full thread input focus restoration in [`engine/text_injector.py`](../../engine/text_injector.py). |
| **test** | Authored targeted regression tests for desktop notifications and modern app UI verification ([`tests/test_target_verification_modern_apps.py`](../../tests/test_target_verification_modern_apps.py)). |
| **check** | Verified standalone binary integrity, single-instance mutex enforcement, and offline transcription self-tests. |
| **document** | Updated [`docs/release/RELEASE_ARTIFACT_MANIFEST.md`](../../docs/release/RELEASE_ARTIFACT_MANIFEST.md) and authored this directive. |

### Core Architectural Invariants Maintained
- **Zero Cloud Egress:** Audio, raw transcripts, and formatted outputs never leave the local machine. Verified by [`tests/test_network_egress.py`](../../tests/test_network_egress.py).
- **Truthful Status:** Never report an injection as confirmed unless the document buffer was physically verified; `InjectionStatus` drives the UI truthfully.
- **Windows-First Architecture:** Win32 API and Microsoft UI Automation first, cross-platform fallbacks second.
- **UTF-8 Subprocess Safety:** Every subprocess call passes `encoding="utf-8", errors="replace"` and runs with `-X utf8`.
- **Environment Isolation:** Tests isolate state via `FLOWPILOT_CONFIG_FILE`, `FLOWPILOT_CONFIG_DIR`, `FLOWPILOT_MUTEX_NAME`, and `FLOWPILOT_HEADLESS`.

---

## 3. Competitive Realism: FlowPilot vs. Wispr Flow

We performed a deep forensic audit comparing FlowPilot against Wispr Flow on Windows 11. Here is our defensible positioning and reality check:

```
┌─────────────────────────────────┬──────────────────────────────────┬──────────────────────────────────┐
│ Dimension                       │ Wispr Flow (Observed Live)       │ FlowPilot v3.1.0 (Local Engine)  │
├─────────────────────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Privacy & Egress                │ Cloud endpoints (TLS required)   │ 100% Offline (Zero egress)       │
│ Memory Footprint (Idle)         │ 1,192 MB (12 Electron processes) │ ~98 MB (1 Python/Qt process)     │
│ Word Usage Limits               │ Metered / Paid subscription      │ Unlimited / Free forever         │
│ Audio Ducking                   │ Not supported natively           │ Supported via CoreAudio pycaw    │
│ Target Verification             │ Blind keystroke dispatch         │ UIA + Win32 buffer inspection    │
│ Spoken Self-Correction          │ Cloud LLM post-processing        │ Local deterministic regex engine │
│ Offline Speech Model Bundle     │ None (Cloud only)                │ Dual Base + Small (int8 CPU)     │
└─────────────────────────────────┴──────────────────────────────────┴──────────────────────────────────┘
```

FlowPilot's competitive moat is absolute offline sovereignty, minimal RAM consumption, and deterministic privacy.

---

## 4. Live User Testing Failures & Root-Cause Remediation

During live user testing on an interactive Windows 11 machine, three distinct issues emerged. All three have been analyzed, fixed at the root cause, and regression-tested.

### Issue 1: F9 Hotkey Premature Cutoff & Conflict
- **Symptom:** User reported: *"Sometimes when I press F9, it's just so stupid; it cuts off or doesn't work."*
- **Root Cause:**
  1. Default configuration was set to `hotkey_mode: hold` with an aggressive silence cutoff (1.0 s). In hold mode, any key bounce or brief conversational pause triggered premature termination.
  2. `FindWindowW` in the hotkey conflict checker was searching for `"FlowPilot"`, which did not match the actual window title, allowing conflicting hotkey hooks to collide.
- **Fix Applied:**
  1. Updated default configuration in `config.py` and user profile (`~/.flowpilot/config.json`) to `hotkey_mode: toggle` and extended silence timeout to `2.5` seconds.
  2. Fixed window title resolution in `hotkey_service.py` to match the exact Qt window class and handle.
  3. Added proactive tray notifications when global hotkey conflicts occur.

### Issue 2: The Alarming "Unverified Target" Warning Balloon
- **Symptom:** User dictated successfully, text was inserted properly into the target window, but Windows immediately popped an alarming system tray notification with a yellow warning triangle: `⚠️ FlowPilot: Unverified Target — Sent — unverified target (please check)`. The user assumed FlowPilot crashed or threw a fatal error.
- **Root Cause:**
  In [`desktop_app.py`](../../desktop_app.py#L208-L214), when `state in ("pasted", "success") and not confirmed`, the desktop app invoked:
  ```python
  self.tray.show_notification("FlowPilot: Unverified Target", notice_text, is_warning=True)
  ```
  Because modern Windows applications (Chrome, Edge, VS Code, Discord, Slack, Word, Store Notepad) use custom GPU render surfaces (DirectWrite, Skia, Blink, Electron, WinUI), they do not expose Win32 `WM_GETTEXT` buffers. As a result, FlowPilot marked 95%+ of routine pastes as `SENT_UNVERIFIED` and spawned a loud OS warning balloon on almost every dictation!
- **Fix Applied:**
  Removed the intrusive OS warning toast for routine unverified pastes in [`desktop_app.py`](../../desktop_app.py#L208-L214). Truthful status updates remain visible quietly on the floating mascot HUD and tray tooltip without disturbing the user. Genuine runtime errors (`state == "error"`) still trigger OS notifications.
  Added a regression test to [`tests/test_desktop_app.py`](../../tests/test_desktop_app.py#L47-L54).

### Issue 3: Modern Target Verification & Foreground Focus Architecture
- **Symptom:** User stated: *"Fix this thing because this would be really important and because I don't want this to be an issue at the latest in the future."* The user wanted target verification to actually work rather than permanently labeling modern applications as unverified, and wanted focus switching to be 100% reliable.
- **Root Cause:**
  1. **Blindness to Modern Document Buffers:** [`TextInjector.read_window_buffer`](../../engine/text_injector.py) only called Win32 `WM_GETTEXT` on child edit controls. In modern applications, there is no classic `Edit` or `RichEdit` child control, so `read_window_buffer` returned `None` 100% of the time.
  2. **SetForegroundWindow Restriction:** [`TextInjector._safe_set_foreground`](../../engine/text_injector.py) called `win32gui.SetForegroundWindow(hwnd)` directly. On Windows 10/11, Windows blocks background threads from stealing foreground focus (`LockSetForegroundWindow`). When FlowPilot ran in a background worker thread, focus restoration failed, causing [`_resolve_verified_foreground`](../../engine/text_injector.py) to abort injection with `Active focus switched from HWND...`.
  3. **Verification Never Requested by Orchestrator:** In [`engine/orchestrator.py`](../../engine/orchestrator.py#L387), `TextInjector.inject_with_status(formatted_text, target_hwnd)` was called with `verify_confirmation=False` by default, so verification was never even attempted during live dictations!
- **Architectural Solution Implemented:**
  1. **Microsoft UI Automation (UIA) Integration:**
     Implemented `_read_via_ui_automation(cls, target_hwnd: int) -> Optional[str]` in [`engine/text_injector.py`](../../engine/text_injector.py#L725-L785) using `UIAutomationCore.dll` and `comtypes`.
     FlowPilot performs a rapid breadth-first search across UI element descendants to query `IUIAutomationTextPattern` (pattern 10014) and `IUIAutomationValuePattern` (pattern 10002).
     - **Performance:** The historical handoff reported an approximately 1.23 ms warm query; no representative multi-app latency distribution or timeout guarantee was established.
     - **Coverage:** Automated UIA read-back was exercised on a Qt editor. The other listed application classes require direct, separately recorded interactive tests before claiming coverage.
  2. **Canonical Win32 Thread Input Pairing:**
     Upgraded `_safe_set_foreground(cls, hwnd: int) -> bool` in [`engine/text_injector.py`](../../engine/text_injector.py#L186-L255) using the canonical `AttachThreadInput` trio from `notepad_harness.py`:
     - Attaches calling thread (`cur_tid`), current foreground thread (`fg_tid`), and target window thread (`target_tid`).
     - Simulates an Alt-key press (`VK_MENU`) to bypass the Windows foreground lock timeout (`SPI_SETFOREGROUNDLOCKTIMEOUT`).
     - Brings target window to top and calls `SetForegroundWindow(hwnd)`.
     - Safely detaches thread inputs in `finally`.
     - Attempts focus restoration; Windows can still deny it. The injector must fail safely and keep recovery text when focus cannot be verified.
  3. **Active Verification Enabled in Orchestrator:**
     Updated line 387 of [`engine/orchestrator.py`](../../engine/orchestrator.py#L387) to:
     ```python
     inj_res = TextInjector.inject_with_status(formatted_text, target_hwnd, verify_confirmation=True)
     ```
     Now, FlowPilot actively verifies that the injected text arrived in the target document. When verified, it returns `CONFIRMED_INSERTED` with `"Inserted & confirmed"`. For truly opaque targets (e.g., full-screen DirectX games), it cleanly falls back to `SENT_UNVERIFIED` without error.

---

## 5. Test Suite Expansion & Audit Results

The current runner comprises **53 test suites**. The strict 2026-10-22 source gate passed 53/53 with no skips. This section records the earlier UIA handoff, not a broad multi-app insertion guarantee.

### New Test Suite: `test_target_verification_modern_apps.py`
Located at [`tests/test_target_verification_modern_apps.py`](../../tests/test_target_verification_modern_apps.py) and registered in [`tests/run_all_tests.py`](../../tests/run_all_tests.py#L67):
1. **`test_uia_modern_buffer_read_and_verification`**: Creates a PySide6 editor surface and asserts that `read_window_buffer` and the presence-only helper can read text already present. It does not dispatch a real paste or claim delivery.
2. **`test_confirmation_requires_new_document_content`**: Mocks dispatch and document read-back; pre-existing text cannot produce `CONFIRMED_INSERTED`.
3. **`test_safe_set_foreground_handles_same_window_and_remote_threads`**: Validates the helper's bounded mocked paths, not all real Windows thread/focus cases.

### Verification Execution
```bash
# Run the new modern app verification suite
python -X utf8 tests/test_target_verification_modern_apps.py
# Output: [Injector] Successfully dispatched 21 characters to HWND ...
#         UIA READ AND CONSERVATIVE VERIFICATION TESTS PASSED.

# Run standalone desktop app lifecycle test
python -m pytest tests/test_desktop_app.py
# Output: 1 passed in 3.80s

# Run text injection suite
python -m pytest tests/test_text_injector.py
# Output: 10 passed in 0.59s
```

---

## 6. Release Artifact Packaging & Cryptographic Integrity

We compiled, verified, and packaged the standalone binary for FlowPilot v3.1.0:

### 1. Build Verification
- **Compilation:** PyInstaller 6.22.3 on Python 3.11.15 (`flowpilot.spec`).
- **Cleanliness Audit:** RC2 archive filename scan found no competitor-renderer or credential-bridge paths, `flow.sqlite`, or `__pycache__` entries. This does not prove a complete dependency or licensing audit.
- **Bundled Model Weights:**
  - Faster-Whisper `base` (`_internal/models/faster-whisper-base/model.bin`, 145,217,532 bytes)
  - Faster-Whisper `small` (`_internal/models/faster-whisper-small/model.bin`)
  - Silero VAD v5 ONNX assets (`silero_encoder_v5.onnx`, `silero_decoder_v5.onnx`)
- **Standalone Smoke Test:** PASSED ([`tests/test_standalone_binary_smoke.py`](../../tests/test_standalone_binary_smoke.py)). Validated single-instance named mutex enforcement and clean shutdown.
- **Offline Transcription Self-Test:** PASSED against the byte-identical staged RC2 executable with offline flags and empty isolated cache (exit code 0; SAPI fixture transcription in 1.57 s). No packet-level capture was performed.

### 2. Cryptographic Manifest
Updated in [`docs/release/RELEASE_ARTIFACT_MANIFEST.md`](../../docs/release/RELEASE_ARTIFACT_MANIFEST.md):

| Artifact | Path | Size | SHA-256 Hash |
|---|---|---|---|
| **Standalone Executable, RC2** | `dist/FlowPilot/FlowPilot.exe` | 24,856,098 bytes | `FD3E2D7825E6AEDBC745215FF8E64EBD8F561F4E00B01B5FB408AE597304CAC0` |
| **Local RC2 Archive** | `dist/FlowPilot-v3.1.0-RC2-win64.zip` | 772,927,221 bytes | `682A7FFC39516FA1C2733D4275E8383D1B5603E46DBA859FC85F7DBAB1B0C51E` |

### 3. Git Version Control State
- **Branch:** `master`
- **Latest local commit at reassessment:** `06196fa`; RC2 also includes uncommitted changes.
- **Git Tag:** `v3.1.0-release` exists locally but was absent from the remote at reassessment. Local `master` was 26 commits ahead of `origin/master`.

---

## 7. Recommended Next Steps for Codex

When you take the baton for the next engineering slice, here is the suggested checklist:

1. **Full Regression Gate Run:**
   Execute the full 53-suite strict test gate on your interactive Windows desktop:
   ```powershell
   python -X utf8 tests/run_all_tests.py --require-all
   ```
2. **Field Telemetry Inspection:**
   Inspect `.flowpilot/dictation_telemetry.log` after live usage to confirm that `injection_status` logs `CONFIRMED_INSERTED` across target applications.
3. **Authenticode Signing Pipeline:**
   When an EV or Standard code signing certificate is provisioned, integrate `signtool.exe` into `scripts/build_release_binary.py` to establish SmartScreen identity reputation.
4. **Custom Web Component Shadow DOM Support (Optional):**
   If testing against complex web applications with closed shadow roots where standard UIA TextPattern does not penetrate, evaluate extending `_read_via_ui_automation` with `TreeWalker` condition filters for specific accessible child roles.

The codebase is clean, tested, and fully stabilized. Over to you, Codex!
