# FlowPilot Engineering Directive & Verification Handoff to Codex

**Document Version:** 3.2.0<br/>
**Date:** 2026-10-19<br/>
**Author:** Pair Programming Agent (Gemini)<br/>
**Recipient / Reviewer:** Codex (Technical Partner & Architecture Reviewer)<br/>
**Status:** Historical 2026-10-19 handoff (38-suite result); not current release status. See the [2026-10-22 reassessment](../reviews/2026-10-22-release-reassessment.md) for the 53-suite source gate and unpublished RC2 artifact.

---

## 1. Executive Context & Acknowledgment

This directive serves as the formal engineering update, verification protocol, and commercial protection baseline for Codex.

We explicitly acknowledge and retain the critical audit contributions Codex delivered to the repository:
1. **Elimination of Unsubstantiated Claims:** Halting inflated assertions (e.g. "99.9% paste reliability") and establishing clear distinctions between headless CI passes (35 passed, 2 hardware skips) and live Windows desktop verification.
2. **Commercial Surface Protection:** Moving internal pilot decks, enterprise agreements, pricing matrices, and participant interview protocols out of public repository tracking into Git-ignored [`private/pilot/`](../../private/pilot/).
3. **Data Integrity & Privacy Realism:** Exposing that the History Vault previously saved audio WAVs by default, and enforcing `save_history_text: false` as the default across all fresh profiles with zero-vault creation.
4. **Third-Party Attribution:** Documenting the SondeR-Cat pixel assets under the Apache-2.0 license (Verisonder notice) in [`THIRD_PARTY_LICENSES.md`](../../THIRD_PARTY_LICENSES.md).

All engineering work completed in this cycle builds directly upon these rigorous boundaries.

---

## 2. Commercial Angle & Intellectual Property Protection

To protect FlowPilot's commercial viability and competitive defensibility while maintaining open-source hygiene:

1. **Strict Private Directory Isolation:**
   - [`private/pilot/`](../../private/pilot/) must remain permanently in [`.gitignore`](../../.gitignore). Never stage, commit, or push files from this directory to any public branch.
   - All commercial pilot metrics, enterprise pricing documents, customer validation data, and partner strategy notes reside exclusively in `private/pilot/`.

2. **Original Character IP & Visual Independence:**
   - FlowPilot no longer relies on third-party mascot art for its core identity.
   - We have established FlowPilot's original visual suite in [`ui/companion_renderer.py`](../../ui/companion_renderer.py) and registered it in [`engine/companion_assets.py`](../../engine/companion_assets.py):
     - **Signal (Default):** Calm, distraction-free neutral capsule indicator with an audio-driven 5-bar envelope and 3-dot processing state.
     - **Pilot (Mascot):** Original 24×24 pixel cybernetic courier robot with voice-reactive antenna glow and visor expressions.
     - **Seedling (Concept 2):** Original 24×24 pixel sleepy seed creature whose leaf awakens during listening and blooms on successful paste.
     - **Nimbus (Concept 3):** Original 24×24 pixel vapor cloud sprite with an internal bioluminescent glow core.
   - **SondeR-Cat** remains available as an optional open-source companion, fully attributed under Apache-2.0.

3. **Zero Network Egress & Sovereign Enterprise Guarantee:**
   - Offline local inference (Faster-Whisper int8 on CPU) remains inviolable.
   - No telemetry, analytics, cloud transcription fallbacks, or crash reporting tokens are transmitted over the wire.
   - Verified by forensic egress tests ([`tests/test_network_egress.py`](../../tests/test_network_egress.py)).

4. **Honest Competitive Observation Boundaries:**
   - In head-to-head benchmarking against Wispr Flow, closed-source protocols, internal injection heuristics, and encrypted TLS traffic remain labeled **"Not measured / Unknown"** unless verified through lawful, attributed observation.
   - No persistent certificate authority has been injected into Windows trust stores, and no user credentials or personal dictations have been used.

---

## 3. Engineering Hardening & Bug Fixes Delivered

### A. Windows 11 Notepad Focus & Child HWND Insertion
- **Root Cause Identified:** On Windows 11 (22H2+ / Build 26200+), `Notepad.exe` hosts its editable surface inside a child window of class `RichEditD2DPT` beneath `Windows.UI.Input.InputSite.WindowClass`. Testing `GetForegroundWindow() != target_hwnd` caused false aborts because foreground belonged to the top-level parent or input bridge.
- **Surgical Patch Applied:**
  - Introduced `_is_same_window_hierarchy(hwnd1, hwnd2)` utilizing `win32gui.GetAncestor(hwnd, GA_ROOT)` in [`engine/text_injector.py`](../../engine/text_injector.py).
  - Focus guard now permits dispatch if the foreground window shares the same top-level root hierarchy.
  - Test harness ([`tests/notepad_harness.py`](../../tests/notepad_harness.py)) completely eliminated synthetic `WM_PASTE` backdoors. All verifications use honest `NotepadPasteResult(verified, retries, first_attempt_success, recovered, status, error)`.
  - Non-invasive `WM_GETTEXT` on the owned `RichEditD2DPT` control physically confirms text presence without modifying clipboard state.

### B. Sub-Desktop Runner Station Isolation
- **Mechanism:** In headless or automated test sessions (`exebox-...`), `GetForegroundWindow()` frequently returns `0`.
- **Hardening:** Added `_resolve_verified_foreground()` polling up to 100 ms. If foreground remains `0`, the injector aborts safely with `InjectionStatus.FAILED_RECOVERY_AVAILABLE`, retaining the dictation text in `TextInjector.last_injected_text` without clobbering the user's existing system clipboard.

### C. Deterministic Mutex Packaging Smoke Test
- Hardened [`tests/test_standalone_binary_smoke.py`](../../tests/test_standalone_binary_smoke.py) by replacing memory heuristics (`RSS > 120MB`) with native Win32 `kernel32.OpenMutexW(SYNCHRONIZE, False, mutex_name)`. The secondary instance detects the primary mutex deterministically in under 2 seconds.

### D. Unified Companion & Motion Engine
- Implemented [`ui/companion_renderer.py`](../../ui/companion_renderer.py) as the single source of truth for both [`FloatingHUD`](../../ui/floating_hud.py) and [`CompanionStudioDialog`](../../ui/companion_studio.py).
- Enforced complete reduced-motion suppression: freezing all procedural physics, eye blinking, paw kneading, and waveform flutter into static resting/listening symbols.
- Added elapsed-time phase calculations with integer device-pixel grid snapping across 100%–200% DPI.

---

## 4. Sovereign Meeting Deliberation & Intelligence Architecture

In direct parity and leapfrog over cloud notetakers (e.g., Wispr Flow Notetaker), FlowPilot now incorporates a 100% offline call intelligence slice:

1. **Guided AI Deliberation Engine ([`engine/meeting_deliberation.py`](../../engine/meeting_deliberation.py)):**
   - **"What Did I Miss?" Live Catch-Up (`generate_catchup`):** Extracts salient points and immediate action items from the previous 5-minute rolling window without interrupting continuous recording.
   - **Decision Weighing Matrix (`extract_weighing_matrix`):** Lexical heuristic contrastive extraction parses architectural alternatives, pro/con trade-offs, and consensus vs. open debate states.
   - **Risk & Blocker Radar (`extract_risk_radar`):** Scans statements for technical, operational, and security risks, tagging severity (`HIGH` vs `MEDIUM`) with mitigation hints.
   - **Agentic Action Dispatcher (`generate_followup_email` & `generate_task_cards`):** Auto-generates Markdown executive follow-up email drafts and Jira/GitHub formatted task cards with priority heuristics and acceptance criteria.
   - **Granular Retention Enforcement (`RetentionPolicy`):** Auto-purges local session files on 7, 30, 90, 365-day policies (or indefinite retention) strictly on local disk with zero cloud sync.

2. **Native Real-Time Speech Translation ([`engine/stt_engine.py`](../../engine/stt_engine.py)):**
   - Directly configures Faster-Whisper local model with `task="translate"`, natively mapping foreign speech input to English text on CPU with zero network calls.

3. **Meeting Studio View Integration ([`ui/notetaker_view.py`](../../ui/notetaker_view.py)):**
   - Added `🌐 Translate: OFF / EN` mode toggle.
   - Added `⚡ Catch Up` live recap button.
   - Added Tab 4 `⚖️ Deliberation` studio featuring the Decision Weighing Matrix, Risk Radar, and 1-click clipboard actions for emails and task cards.
   - Automatic integration with [`engine/insights_engine.py`](../../engine/insights_engine.py) tracking meeting duration, decisions reached, action items created, and deep work ratio.

---

## 5. Empirical VB-Cable Benchmark Execution (FlowPilot Baseline)

On 2026-10-18, a 15-trial empirical benchmark was conducted over official VB-Audio Virtual Cable (WASAPI 48 kHz). Identical 16-bit PCM speech fixtures were routed through `CABLE Input` (14) into `CABLE Output` (18). FlowPilot transcription and ContextProcessor formatting were executed locally; Wispr Flow was observed running concurrently as a host process, but its closed-session transcription outputs were not captured in this run.

Detailed run manifest and raw data are preserved in the tracked repository location [`docs/testing/vbcable_benchmark_results.json`](../testing/vbcable_benchmark_results.json) and documented in [`docs/testing/WISPR_FLOW_HEAD_TO_HEAD.md`](../testing/WISPR_FLOW_HEAD_TO_HEAD.md):

```text
================================================================================
             FLOWPILOT EMPIRICAL BENCHMARK SUMMARY (SYNTHETIC SAPI CORPUS)
================================================================================
Total Trials Executed:                 15
Transcription + Formatting (p50):      549.5 ms
Transcription + Formatting (p95):      939.6 ms
Mean Cleaned Word Error Rate (WER):    9.51% (against cleaned references)
Mean Raw ASR WER:                      18.60% (against raw references)
Developer Identifier Accuracy:         93.8% (15/16 tokens matched on corpus)
Factual Token (Numbers/Negations):     87.5% (35/40 tokens preserved on corpus)
Negation Preservation Rate:            100.0% (NS-01 & NS-02 preserved)
FlowPilot Host Memory (RSS):           282.4 MB (4 observed python processes before model load)
Wispr Flow Resident Memory (RSS):      1,192.9 MB (12 child processes snapshot)
Network Egress:                        0 bytes (Forensically verified)
================================================================================
```

### Key Analytical Takeaways
1. **Formatting Rules on Synthetic Corpus:** On this 15-phrase synthetic SAPI corpus, raw Whisper `base` scored an 18.60% WER against raw references, while FlowPilot's ContextProcessor & FactGuard scored **9.51%** against cleaned references, successfully preserving technical tokens and tested negations.
2. **Resource Footprint:** FlowPilot was observed at **282 MB RAM** across 4 host python processes before model load, compared to Wispr Flow's 12-process Electron/Node tree observed at **1.19 GB RAM**.
3. **Sub-second Local Processing:** Even on a 22.3-second technical passage (`LP-01`), end-to-end local transcription and formatting resolved in **765.8 ms** on CPU without cloud latency. (Note: In headless batch runs without a target window, injection returns `FAILED_RECOVERY_AVAILABLE`, so visible text insertion latency is measured separately on active desktop sessions).

---

## 6. Codex Independent Verification Protocol

Codex can independently reproduce and verify this entire state using the following steps:

### Step 1: Verify Clean Git State & Worktree
```powershell
# Verify dirty worktree is preserved and no private drafts are staged
git status --short
```
*Expected:* All modified files match known development state; zero tracked files under `private/pilot/`.

### Step 2: Run the Full 38-Suite Automated Regression Gate
```powershell
python tests/run_all_tests.py
```
*Expected Result:*
```text
Total Test Time: ~109s | Overall Verdict: ALL TESTS PASSED (38 / 38)
```

### Step 3: Verify Meeting Deliberation & Intelligence Suites
```powershell
pytest tests/test_meeting_deliberation.py tests/test_meeting_notetaker.py tests/test_meeting_notetaker_v2.py tests/test_insights_engine.py -v
```
*Expected Result:* 23 passed in < 5.0s across meeting deliberation, notetaker engine, library management, and insights.

### Step 4: Verify Companion Studio & Renderer Contract
```powershell
pytest tests/test_companion_studio.py tests/test_pixel_companions_and_creator.py -v
```
*Expected Result:* 25 passed in < 2.0s (18 in studio, 7 in pixel companions).

### Step 5: Verify VB-Cable 48 kHz WASAPI Loopback
```powershell
python scratch/test_vbcable_loopback.py
```
*Expected Result:* RMS > 0.05, Peak > 0.1 on WASAPI endpoints 14 & 18.

### Step 6: Reproduce the Paired Acoustic Benchmark
```powershell
python scratch/run_vbcable_paired_benchmark.py
```
*Expected Result:* 15/15 trials pass loopback transmission, writing results to `scratch/vbcable_benchmark_results.json`.

---

## 7. Actionable Next Milestones (Sprints 3B & 3C)

1. **Target-Aware Clipboard Dwell (Sprint 3B):**
   - Implement an explicit in-memory `DictationSession` recovery buffer keyed by session token.
   - Add a separate, user-visible **Paste Last** action alongside **Copy Last** in the HUD context menu.
   - Configure dynamic clipboard restoration dwell: 0.5s for standard Win32 edit controls, 2.0s for Electron/browser editors, 3.5s for virtual desktop / RDP connections.

2. **Local Focused-Field Context Reader (Sprint 3C):**
   - Build a read-only Windows UI Automation (UIA) worker in an isolated background thread.
   - Bound COM worker execution with a strict **500 ms deadline** before falling back to window-title profiles.
   - Enforce immediate rejection on password controls (`IsPassword == True`) and credit card input types.
   - Restrict context extraction to at most 128 characters around the caret; zero screenshots and zero network egress.

---

*FlowPilot Engineering — Verified, Defensible, and Grounded in Reality.*
