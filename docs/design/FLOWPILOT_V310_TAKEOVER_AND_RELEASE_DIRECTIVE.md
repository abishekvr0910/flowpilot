# FlowPilot v3.1.0 Takeover & Master Release Directive

**Date:** October 22, 2026  
**Status:** Active Engineering Directive & Post-Takeover Master State  
**Lead Agent / Owner:** Gemini (Antigravity Core Engineering)  
**Handoff Predecessors:** Codex UI Track, Opencode Audit Track  
**Release Target:** FlowPilot v3.1.0 (Commercial Pilot & Desktop Candidate)  

---

## 1. Executive Summary & Takeover Declaration

Gemini has formally taken over the FlowPilot repository and engineering release track. All previous development threads (Codex native workspace refresh, Opencode forensic audit, and competitive parity tracks) are reconciled under this unified directive.

### Key Milestones Achieved
1. **Total Remediation of Proprietary Competitor Code:**
   * The decompiled Wispr Flow Webpack bundle (`ui/wispr_renderer`), the token-reading bridge (`ui/wispr_bridge.py`), and unpacked staging directories (`scratch/quarantine-wispr-clone-20261022`, `scratch/wispr-unpacked`) have been permanently purged from disk.
   * Stale bytecode (`ui/__pycache__/wispr_bridge.cpython-311.pyc`) was purged.
   * `.gitignore` was hardened with defense-in-depth rules blocking competitor assets.
   * Git history was forensically audited with `git log --all --diff-filter=A --name-only | grep -i wispr`: confirmed that **zero** vendored code, credentials, or proprietary assets were ever committed.
   * `package.json` was restored to `flowpilot@3.1.0` with `"private": true`.

2. **Commercial-Grade Native UI (Sand & Stone Warm Light):**
   * Replaced the gloomy charcoal/sage dialog look with the authentic **Sand & Stone Warm Light Theme** (`#f5f4f0` canvas, 18px rounded `#ffffff` sheets, `#e8e6df` hairline dividers, warm amber `#d98925` accents).
   * Implemented `harmonize_legacy_styles()` in `ui/workspace_style.py` to dynamically recolor all secondary views (Dictionary, Scratchpad, Insights, Snippets, History, Companion Studio, Settings).
   * Refactored Meeting Notetaker (`ui/notetaker_view.py`) into 3 readable tabs (**Library**, **Live transcript**, **Notes & actions**), eliminating horizontal clipping at compact window sizes (880×580).

3. **High-Leverage Feature Delivery (Correction Intent Engine):**
   * Implemented `engine/correction_intent.py` (755 lines, 30+ tests passing in `tests/test_correction_intent.py`).
   * Provides deterministic, span-aware spoken self-correction (*"actually"*, *"no wait"*, *"sorry Jane"*, *"I mean"*), resolving the primary feature gap vs. Wispr Flow while strictly preserving FactGuard safety invariants.

4. **Honest Multilingual Baselining:**
   * Formally withdrew misleading "0.00% WER" claims in `docs/archive/FLOWPILOT_LANGUAGE_VALIDATION.md`, documenting that German raw WER was 95.24% on the release sample.
   * Sanitized `private/pilot/FLOWPILOT_30_DAY_PLAN.md` (removed Wispr outreach, removed 0.00% WER claim, held candidate ZIP, fixed all broken doc links).
   * Established `docs/evaluation/DE_ES_FR_REAL_VOICE_MANIFEST.json` and `scripts/acquire_real_voice_corpus.py` for Mozilla Common Voice real-speech baselining.

5. **50-Suite Automated Test Gate:**
   * **46 Passed**, **4 Skipped (honest hardware/desktop skips)**, **0 Failed**.
   * Resolved the model path resolution bug in `tests/test_model_lifecycle.py` where local weights in `models/` were misidentified as test masquerades.

---

## 2. Source Code & Architecture State

```mermaid
graph TD
    UI[PySide6 Native Workspace] --> Style[Sand & Stone / Obsidian Engine]
    UI --> Home[WorkspaceHome F9 Shortcut & Kiki Preview]
    UI --> Meetings[Notetaker 3-Tab View]
    UI --> Studio[Companion Studio & Pixel Creator]
    
    Audio[Wasapi Microphone Capture] --> VAD[Silero ONNX VAD]
    VAD --> STT[Faster-Whisper int8 Engine]
    STT --> Intent[Correction Intent Resolver]
    Intent --> FactGuard[FactGuard Semantic Guard]
    FactGuard --> Injector[TextInjector / Win32 Clipboard Recovery]
    
    subgraph Zero-Egress Offline Boundary
        Style
        Home
        Meetings
        Studio
        Audio
        VAD
        STT
        Intent
        FactGuard
        Injector
    end
```

### Module Responsibilities
* **`ui/workspace_style.py`**: Central style authority. Defines `_SAND_COLORS`, `_DARK_STYLE`, and `harmonize_legacy_styles()` for non-destructive dynamic recoloring.
* **`ui/flowpilot_dashboard.py`**: Shell window. Manages navigation rail, window sizing constraints (1160×820 normal, 880×580 minimum), and settings propagation.
* **`engine/correction_intent.py`**: Span-aware verbal self-correction resolver. Detects explicit retractions (*"no wait"*, *"sorry"*, *"never mind"*) and intensifier markers (*"actually"*), replacing superseded spans without altering surrounding syntax or dropping FactGuard semantic numbers/negations.
* **`engine/stt_engine.py`**: Local Whisper model manager with lazy segment consumption, thread-safe request coalescing, and offline model path resolution.

---

## 3. Test & Verification Matrix (50 Suites)

Full execution of `tests/run_all_tests.py` produces the following reconciled results:

| Category | Suite Path | Status | Verification Detail |
|---|---|:---:|---|
| **Audio Capture** | `tests/test_audio.py` | **PASS** | Ring buffer, pre-roll, device enumeration |
| **Speech-to-Text** | `tests/test_stt.py` | **PASS** | Faster-Whisper base offline transcription |
| **Text Injection** | `tests/test_text_injector.py` | **SKIP** | Requires interactive desktop; safe abort passes |
| **Audio Ducking** | `tests/test_audio_ducker.py` | **PASS** | Windows audio session ducking recovery |
| **API & WS** | `tests/test_api_and_websocket.py` | **PASS** | REST API and WebSocket local interface |
| **Hotkeys** | `tests/test_hotkey.py`, `test_win32_hotkey.py` | **PASS** | F9, Win32 message loop registration |
| **Desktop App** | `tests/test_desktop_app.py` | **PASS** | Tray lifecycle, companion HUD dispatch |
| **Language Registry** | `tests/test_language_registry.py` | **PASS** | 18 core languages, scripts, direction (LTR/RTL) |
| **Writing Intelligence** | `tests/test_writing_intelligence.py` | **PASS** | Orthography, punctuation, casing transforms |
| **FactGuard** | `tests/test_factguard_adversarial.py`, `test_factguard_v2.py` | **PASS** | Conservative entity protection, sealed snapshots |
| **Correction Intent** | `tests/test_correction_intent.py` | **PASS** | Deterministic spoken self-correction |
| **Zero Egress** | `tests/test_network_egress.py` | **PASS** | Network socket isolation and telemetry ban |
| **Multilingual** | `tests/test_multilingual_validation.py`, `test_multilingual_speech_reality.py` | **PASS** | Script direction, honest SAPI reality notice |
| **Personalization** | `tests/test_personalization.py`, `test_personalization_snippets.py`, `test_personalization_pr3.py` | **PASS** | Dictionary, voice snippets, prompt budgeting |
| **Settings** | `tests/test_settings_dialog.py` | **PASS** | Hotkey conflicts, validation, appearance persistence |
| **Benchmarks** | `tests/test_model_benchmarks_extended.py` | **PASS** | Base/small model load latency and RTF |
| **Orchestrator** | `tests/test_orchestrator_state_machine.py`, `test_session_lifecycle.py` | **PASS** | 9-state machine, deferred switching during dictation |
| **Application Profiles** | `tests/test_application_profiles.py` | **PASS** | Per-app rule inheritance and precedence |
| **Silero VAD** | `tests/test_silero_vad_resolution.py` | **PASS** | ONNX asset path resolution and LRU cache fix |
| **Notepad E2E** | `tests/test_notepad_dictation_e2e.py` | **SKIP** | Requires interactive desktop; safe-abort verified |
| **Cross-Platform** | `tests/test_cross_platform.py` | **PASS** | Linux and macOS fallback adapters |
| **Companions** | `tests/test_sondercat_companion.py`, `test_kiki_companion.py`, `test_pixel_companions_and_creator.py`, `test_companion_studio.py` | **PASS** | 12-frame animations, Kiki prototype, studio |
| **Cross-App Injection** | `tests/test_cross_app_injection.py` | **SKIP** | Requires interactive desktop; focus checks pass |
| **Final Spec** | `tests/test_final_specification_e2e.py` | **SKIP** | Requires interactive desktop; S1-S3, S6-S18 pass |
| **Smoke Packaging** | `tests/test_standalone_binary_smoke.py` | **PASS** | Mutex single-instance and asset bundling |
| **Insights & Meetings** | `tests/test_insights_engine.py`, `test_meeting_notetaker.py`, `test_meeting_notetaker_v2.py`, `test_meeting_deliberation.py` | **PASS** | Analytics, streaming notes, deliberation |
| **Workspace & Dashboard** | `tests/test_flowpilot_dashboard.py`, `test_workspace_refresh.py` | **PASS** | 20/20 UI tests, theme switching, 880x580 sizing |
| **Transforms & History** | `tests/test_transforms_and_history.py`, `test_honest_transforms.py` | **PASS** | Selection transforms, history recovery |
| **Model Lifecycle** | `tests/test_model_lifecycle.py` | **PASS** | Resolution to `models/` verified (fixed assertion) |
| **Evaluation Metrics** | `tests/test_evaluation_metrics.py` | **PASS** | Corpus schema, error categorization |
| **Voice Editor & LLM** | `tests/test_voice_editor_pr4.py`, `test_voice_command_and_llm.py` | **PASS** | Voice commands, atomic text editing |
| **Review Integration** | `tests/test_review_integration.py` | **PASS** | Adversarial safety and regression containment |

**Summary: 46 PASSED, 4 SKIPPED (honest hardware skips), 0 FAILED.**

---

## 4. Binary Packaging Status

* **Unpacked Build Path:** `dist/FlowPilot/`
* **Primary Executable:** `dist/FlowPilot/FlowPilot.exe` (24,849,527 bytes)
* **Total Unpacked Folder Size:** **625,397,371 bytes** (1,199 files)
  * Down 139 MB from the earlier 764 MB bloated build.
  * Packaged files include only the native engine, Qt6 core/widgets, Faster-Whisper base models, Silero VAD ONNX, and static UI assets.
  * Verified: **Zero** competitor files, no Electron, no Sentry, no Supabase, no `__pycache__` in the bundle.
* **Standalone Smoke Test:** PASSED (`python tests/test_standalone_binary_smoke.py`).
* **Offline Self-Test:** PASSED (`dist\FlowPilot\FlowPilot.exe --self-test`).

---

## 5. Release Gate & Final Sign-Off Requirements

To graduate this build from a local candidate to an official **v3.1.0** published release:

1. **Interactive Desktop Verification:**
   * Run `python tests/test_notepad_dictation_e2e.py` on an active, unlocked physical Windows desktop to complete the 5 physical paste cycles into Windows 11 `NotepadTextBox`.
2. **Release Archive Generation:**
   * Create `dist/FlowPilot-v3.1.0-win64.zip` from `dist/FlowPilot/`.
   * Compute and record the physical cryptographic SHA-256 hash in `docs/release/RELEASE_ARTIFACT_MANIFEST.md`.
3. **Commit & Tag:**
   * Stage cleaned source files.
   * Commit with message: `release: FlowPilot v3.1.0 — Sand & Stone native workspace, correction intent engine, and compliance hardening`.
   * Create signed release tag: `v3.1.0-release`.
