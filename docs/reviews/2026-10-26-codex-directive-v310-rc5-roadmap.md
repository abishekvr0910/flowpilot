# FlowPilot Engineering Directive to Codex: v3.1.0-RC5 Integration & Next Priorities

**Date:** 2026-10-26  
**Target Agent:** Codex  
**Originating Agent:** Antigravity (Pair Programming Lead)  
**Repository State:** `master` synchronized with `origin/master` at commit `a055617`  
**Distribution Target:** Windows x64 Standalone (`v3.1.0-RC5`)

---

## 1. Executive Summary & Repository Status

The peer-reviewed release hardening branch `feature/reviewed-v310` has been successfully reconciled, verified, and merged into `master` at commit `4b7bbca`, followed by the release artifact manifest update at commit `a055617`. Both commits have been pushed cleanly to remote `origin/master`.

The isolated review worktree (`scratch/worktrees/reviewed-v310`) and branch have been removed. The active working tree is completely clean.

### Test Audit Summary (Full 58-Suite Suite Gate)
Execution command:
```powershell
$env:FLOWPILOT_HEADLESS='1'; $env:QT_QPA_PLATFORM='offscreen'; python -X utf8 tests/run_all_tests.py
```
- **Total Suites:** 58
- **Passed:** 53 suites (100% of headless automated suites)
- **Skipped:** 5 suites (legitimate interactive desktop suites requiring physical input focus/audio devices: `test_text_injector.py`, `test_notepad_dictation_e2e.py`, `test_cross_app_injection.py`, `test_final_specification_e2e.py`, `test_target_verification_modern_apps.py`)
- **Failed:** 0 suites
- **Execution Time:** 176.34 seconds

### Verified Release Artifacts
- **Zip Archive:** `dist/FlowPilot-v3.1.0-RC5-win64.zip` (770,701,235 bytes)
- **Archive SHA-256:** `8B57F3C74EB05874AE2C5839767567A33DBF2613E9873ECB4E6950AD6B276713`
- **Embedded Executable:** `FlowPilot.exe` (24,908,667 bytes, SHA-256: `AEB7F817B7E2482A18EE52123C3F1F24327D9779F9D79A2139E8FDAC32C5145C`)
- **Manifest:** Formally documented in `docs/release/RELEASE_ARTIFACT_MANIFEST.md`.

---

## 2. Changes Integrated & Invariant Enforcement

Codex must review the following key architectural behaviors now established on `master`:

1. **Recovery Generation Counters (`engine/orchestrator.py`):**
   - The orchestrator maintains monotonic generation counters (`_last_transcription_generation` and `_last_injection_generation`).
   - The recovery hotkeys (`Shift + Alt + X` for raw transcript restore, `Shift + Alt + Z` for formatted text re-paste) only act on the active or most recent generation. If a new recording session begins or the buffer is cleared, stale text cannot be accidentally injected into subsequent windows.
   - Guarded by tests in `tests/test_recovery_feedback.py`.

2. **Truthful Status & Model Verification (`ui/settings_dialog.py`, `ui/setup_wizard.py`):**
   - In accordance with the "Truthful Status" invariant, the UI no longer reports a model as "verified" simply because its `.bin` weights exist on disk.
   - It displays truthful guidance: *"Local small model file found. The small model is selected for this language. Recognition still needs a real voice check."* Full acoustic verification requires a real voice sample.

3. **Packaging License Integrity (`scripts/package_windows_release.py`):**
   - Root `.gitignore` now specifies `/models/` instead of `models/`, ensuring model license notices in `licenses/models/` (`OpenAI-Whisper-LICENSE.txt` and `Silero-VAD-LICENSE.txt`) are tracked and packaged.
   - Packaging fails closed if any of the 93 required notices are omitted or if unsigned builds attempt to claim signed Authenticode status.

4. **Zero Cloud Egress Floor:**
   - All legacy cloud transcription and obsolete proxy options have been scrubbed from `engine/config.py`, `engine/orchestrator.py`, and `ui/app.js`. Dictation never leaves `127.0.0.1`.

---

## 3. Immediate Next Priorities for Codex

With the release candidate baseline stabilized and published to `master`, Codex should prioritize the following three operational work streams:

### Priority 1: Windows Authenticode Code Signing Pipeline
- **Problem:** `FlowPilot-v3.1.0-RC5-win64.zip` is currently unsigned (`NotSigned`), triggering Windows SmartScreen warnings on end-user machines.
- **Task:**
  1. Inspect `scripts/package_windows_release.py` and build an automated signing wrapper using Windows `signtool.exe` supporting SHA-256 dual-timestamping (`/tr http://timestamp.digicert.com /td sha256`).
  2. Implement a secure certificate discovery mechanism (detecting either local HSM/YubiKey EV hardware tokens, Windows Certificate Store `My` certs by thumbprint, or CI-injected PFX environment variables `FLOWPILOT_SIGN_CERT_BASE64` and `FLOWPILOT_SIGN_PASSWORD`).
  3. Update `.github/workflows/ci.yml` to execute code signing when repository release secrets are present, maintaining fail-safe dry-run execution when secrets are absent.

### Priority 2: Indic Language Onboarding & Model Provisioning (Hindi & Tamil)
- **Problem:** Non-English dictation (Hindi, Tamil, Malayalam) requires the `small` or quantized multilingual Whisper models, but users should not have to manually manipulate Hugging Face directories.
- **Task:**
  1. Enhance `ui/setup_wizard.py` and `ui/settings_dialog.py` with an integrated local model downloader and integrity verifier.
  2. Implement automatic SHA-256 verification of downloaded Whisper CTranslate2 int8 model bundles.
  3. Validate acoustic evaluation metrics using `tests/test_multilingual_validation.py` and `tests/test_multilingual_speech_reality.py` to confirm accurate Devanagari and Tamil script tokenization and zero egress during translation/transcription.

### Priority 3: Target Application Text Injection & Compatibility Adapters
- **Problem:** Different Windows targets (Windows Terminal, VS Code, Slack Electron, Microsoft Word, browser rich-text editors) behave inconsistently when receiving rapid keystrokes or standard clipboard pastes.
- **Task:**
  1. Expand `engine/text_injector.py` using the patterns identified in the Open-Source Landscape Research (adapting FlaUI / Windows UI Automation patterns):
     - Terminal Dual-Mode Adapter: Send text via `WM_CHAR` or console input records rather than raw `Ctrl+V` when targeting `ConsoleWindowClass` or `CASCADIA_HOSTING_WINDOW_CLASS`.
     - Electron / Chromium Buffer Verification: Verify whether accessibility value patterns (`IUIAutomationValuePattern`) are accessible to verify character insertion count before claiming success.
  2. Extend `tests/test_target_verification_modern_apps.py` and `tests/test_cross_app_injection.py` to exercise the new adapter pathways.

---

## 4. Architectural Rules & Work Invariants

Codex must strictly maintain all repository rules:
- **Zero Cloud Egress:** Audio, transcription, and prompt data must never leave `127.0.0.1`.
- **Truthful Status:** Never mark text injection as confirmed unless verified by buffer or focus feedback.
- **Stage Environment Variables:** Any test or script modifying configuration must stage `FLOWPILOT_CONFIG_FILE`, `FLOWPILOT_HEADLESS`, or `FLOWPILOT_MUTEX_NAME` prior to importing engine modules.
- **Subprocess Safety:** Every subprocess invocation must pass `encoding="utf-8", errors="replace"` and execute Python children with `-X utf8`.
- **Atomic Commits & Clean Worktrees:** All work should be developed cleanly, tested through the 58-suite audit runner, and verified without leaving dangling worktrees or scaffolds.
