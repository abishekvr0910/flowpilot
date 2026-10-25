# FlowPilot — Peer Review Directive & Local Codebase Audit Packet

**To:** Codex / External Repository Reviewer  
**From:** Antigravity (Pair Programming Architect)  
**Date:** October 26, 2026  
**Target:** Local `master` at commit [`2ee1c4f`](../../CODEX.md) vs. Public GitHub PR #2 / [`4721109`](https://github.com/abishekvr0910/flowpilot/commit/4721109)  
**Scope:** Net `+1972 / −55` across 24 files ahead of public PR #2  
**Suite Status:** 58 suites registered; **53 passed, 5 non-interactive skipped, 0 failed** (Total: 108.54s–119.33s)

---

## 1. Executive Summary for the Reviewer

Public GitHub PR #2 successfully retired obsolete cloud settings, scrubbed historical directives into [`docs/archive/`](../archive/), and introduced strict defensive validation (`OBSOLETE_CLOUD_KEYS` + `HTTP 422`).

In parallel, local `master` implemented critical engineering features, application compatibility expansions, open-source reuse patterns (Sotto, FlaUI), and the authoritative 9-document forensic audit under [`docs/audit/`](../audit/). All changes were reconciled and verified in merge commit `007e8d8`, then finalized with commit `2ee1c4f`.

This packet presents the full technical diff for your independent review, highlighting design choices, implementation details, and specific adversarial stress questions.

---

## 2. Inventory of Functional Upgrades to Review

### Upgrade 1: Terminal Dual-Mode Injection Adapter
- **Files Modified:** [`engine/text_injector.py`](../../engine/text_injector.py), [`tests/test_text_injector.py`](../../tests/test_text_injector.py)
- **Problem Solved:** When users dictate into terminal emulators (`wt.exe`, `cmd.exe`, `powershell.exe`, `alacritty.exe`, `mintty.exe`), standard `Ctrl+V` emits a literal `^V` control character (ASCII `0x16`) or triggers terminal escape sequences.
- **Architectural Solution:**
  - Defined `TERMINAL_APP_PROCESSES = {"cmd.exe", "powershell.exe", "pwsh.exe", "windowsterminal.exe", "wt.exe", "conhost.exe", "alacritty.exe", "wezterm-gui.exe", "kitty.exe", "mintty.exe", "bash.exe", "wsl.exe"}`.
  - Automatically routes paste keystrokes to `Shift+Insert` chords (the universal terminal paste standard) when the target window matches terminal process names or console window classes (`ConsoleWindowClass`, `cascadia`, `terminal`, `mintty`).
  - Applied `post_paste_delay` universally to ensure terminal buffers process keystroke input before focus yields.
- **Unit Verification:** Added `test_terminal_shift_insert_routing()` verifying that `wt.exe` dispatches `VK_SHIFT` + `VK_INSERT` without `VK_CONTROL`, while standard targets (`notepad.exe`) dispatch `VK_CONTROL` + `ord('V')`.
- **Review Scrutiny Point:** Does `Shift+Insert` behave deterministically across customized Windows Terminal JSON profiles where `shift+insert` might be unbound?

---

### Upgrade 2: Transparent Dictation Recovery & Visual HUD Feedback
- **Files Modified:** [`engine/orchestrator.py`](../../engine/orchestrator.py), [`desktop_app.py`](../../desktop_app.py), [`tests/test_recovery_feedback.py`](../../tests/test_recovery_feedback.py), [`tests/run_all_tests.py`](../../tests/run_all_tests.py)
- **Problem Solved:** When target window focus changes during dictation, or when targeting an elevated Administrator window (UIPI block), blind pasting drops text.
- **Architectural Solution:**
  - Registered dedicated global recovery shortcuts: `Shift+Alt+Z` (Paste Last Dictation) and `Shift+Alt+X` (Copy Last Dictation to Clipboard).
  - Wired `re_inject_last()` and `re_copy_last()` methods in `FlowOrchestrator` backed by `TextInjector.last_injected_text` and `last_target_hwnd`.
  - Added visual HUD recovery banner with amber styling and 4-second auto-dismissal.
  - Registered the 58th regression suite: `tests/test_recovery_feedback.py`.
- **Review Scrutiny Point:** Does the recovery buffer handle rapid sequential dictations without race conditions or memory leaks?

---

### Upgrade 3: Application Compatibility & Slow-App Hardening
- **Files Modified:** [`engine/text_injector.py`](../../engine/text_injector.py)
- **Problem Solved:** Complex IDEs and Electron applications (VS Code, Slack, Notion) have asynchronous event loops that drop keystrokes under high CPU load if clipboard hold and dwell times are too fast.
- **Architectural Solution:**
  - Expanded `SLOW_APP_PROCESSES` with modern IDEs (`webstorm64.exe`, `clion64.exe`, `rider64.exe`, `goland64.exe`, `datagrip64.exe`), modern terminals (`windowsterminal.exe`, `wt.exe`), and AI tools (`linear.exe`, `chatgpt.exe`, `claude.exe`).
  - Expanded `_find_edit_control` child window enumeration to recognize `console` and `renderwidget` window classes.
- **Review Scrutiny Point:** Are there any performance regressions introduced by adding new process names to the set lookup?

---

### Upgrade 4: Indic Multilingual Model Verification Badges
- **Files Modified:** [`ui/setup_wizard.py`](../../ui/setup_wizard.py), [`ui/settings_dialog.py`](../../ui/settings_dialog.py)
- **Problem Solved:** South Asian languages (Hindi, Tamil) require the multilingual 244M weights (`faster-whisper-small/model.bin`) to avoid severe script corruption under quantized execution.
- **Architectural Solution:**
  - Checks physical existence of `models/faster-whisper-small/model.bin` on disk.
  - Dynamically updates GUI with green "Verified on Disk" status badges and clear onboarding instructions.
- **Review Scrutiny Point:** Does the path resolution correctly handle custom `FLOWPILOT_MODELS_DIR` overrides?

---

### Upgrade 5: Authenticode Code Signing Automation
- **Files Modified:** [`scripts/package_windows_release.py`](../../scripts/package_windows_release.py)
- **Problem Solved:** Windows SmartScreen displays untrusted publisher warnings on packaged binaries (`FlowPilot.exe`).
- **Architectural Solution:**
  - Added `find_signtool()` to auto-discover Windows 10/11 SDK `signtool.exe` paths.
  - Added CLI flags `--cert`, `--cert-password`, `--signtool` to digitally sign both the application binary and the NSIS installer using SHA256 and RFC 3161 timestamps.
- **Review Scrutiny Point:** Does the packaging script fail gracefully when signing credentials are not supplied?

---

### Upgrade 6: Complete Forensic Audit Deliverables
- **Files Created:** 9 authoritative documents under [`docs/audit/`](../audit/):
  1. `FEATURE_INVENTORY.md`: 55 product features categorized across A–G.
  2. `TECHNICAL_FEATURE_MAP.md`: Sequence diagrams and latency budget.
  3. `TEST_STRATEGY.md`: 5-tier testing pyramid and WER/CER methodology.
  4. `RELIABILITY_RESULTS.md`: Empirical test runner data and memory profiles.
  5. `COMPATIBILITY_MATRIX.md`: App-by-app injection strategies and UIPI handling.
  6. `HYPOTHESIS_REGISTER.md`: Formal tracking of hypotheses H-001 through H-008.
  7. `EXTERNAL_REFERENCES.md`: Comparative research (Sotto, freewispr, PieFlow, FlaUI).
  8. `IMPROVEMENT_ROADMAP.md`: Prioritized 4-phase engineering roadmap.
  9. `AUDIT_SUMMARY.md`: Executive synthesis and release readiness.

---

### Upgrade 7: Clean Workspace & Venture Isolation
- **Action Taken:** Moved untracked scaffold `transcript-cleaner/` out of the FlowPilot repository tree to `S:\APPs\transcript-cleaner`. Recorded architectural rationale in [`docs/research/OPEN_SOURCE_LANDSCAPE_DECISION_2026-10-25.md`](../research/OPEN_SOURCE_LANDSCAPE_DECISION_2026-10-25.md). Retired redundant batch scripts `start_desktop.bat` and `scripts/run_flowpilot.bat`.

---

## 3. Recommended Review Inspection Commands

You can verify the entire diff and test gates using native Git and Python:

```bash
# 1. Inspect full diff against GitHub PR #2
git diff 4721109..master --stat
git diff 4721109..master -- engine/ tests/ ui/

# 2. Verify clean git status and commit lineage
git status
git log -n 6 --graph --oneline

# 3. Run the full 58-suite audit regression runner
python -X utf8 tests/run_all_tests.py

# 4. Run targeted unit tests for new functionality
python -X utf8 tests/test_text_injector.py
python -X utf8 tests/test_recovery_feedback.py
python -X utf8 tests/test_api_and_websocket.py
python -X utf8 tests/test_pilot_reliability.py
```

---

## 4. Specific Adversarial Questions for Your Review

1. **Terminal Injector:** Does `Shift+Insert` provide 100% paste coverage across modern Windows Terminal tab profiles (PowerShell 7, WSL2 Ubuntu, CMD), or should a fallback to direct `SendInput` Unicode typing (`KEYEVENTF_UNICODE`) be attempted if `Shift+Insert` yields no text?
2. **Release Packager:** Is the Authenticode discovery logic robust on systems with multiple Windows SDK versions installed?
3. **Public Readiness:** Are there any remaining internal notes in `docs/audit/` that should be moved to `docs/archive/` prior to public GitHub release promotion?
