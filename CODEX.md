# FlowPilot Engineering Directive & Status Summary for Codex

**Document Version:** 3.2.1<br/>
**Date:** 2026-10-19<br/>
**Current verification note (2026-10-25):** The current working tree defines **58 registered regression suites**; `python -X utf8 tests/run_all_tests.py` executed in 147.77s with **53 passed, 5 non-interactive skipped, 0 failed**. Comprehensive forensic audit findings, feature inventories, and empirical benchmark results are documented in [docs/audit/AUDIT_SUMMARY.md](docs/audit/AUDIT_SUMMARY.md) and [docs/audit/RELIABILITY_RESULTS.md](docs/audit/RELIABILITY_RESULTS.md).
**Primary References:**
- Architectural Handoff: [docs/archive/CODEX_HANDOFF_DIRECTIVE.md](docs/archive/CODEX_HANDOFF_DIRECTIVE.md)
- Core Engineering Policy: [docs/archive/CODEX_DIRECTIVE.md](docs/archive/CODEX_DIRECTIVE.md)
- Empirical Benchmark Protocol & Observations: [docs/testing/WISPR_FLOW_HEAD_TO_HEAD.md](docs/testing/WISPR_FLOW_HEAD_TO_HEAD.md)
- Tracked Benchmark Data: [docs/testing/vbcable_benchmark_results.json](docs/testing/vbcable_benchmark_results.json)
- Privacy & Trust Boundaries: [PRIVACY.md](PRIVACY.md) and [TRUST.md](TRUST.md)

---

## 1. Executive Summary: FlowPilot Offline System vs. Cloud Transcribers

FlowPilot is an air-gapped, local-first dictation and meeting intelligence workstation designed for developers and privacy-conscious users who require sovereign on-device processing.

### Honest Architecture & Feature Comparison

| Dimension | FlowPilot v3.1.0 (Local Device) | Wispr Flow (Cloud-Assisted) | Observations & Measurement Boundaries |
| :--- | :--- | :--- | :--- |
| **Inference Location & Egress** | **100% Local Device** (Faster-Whisper CPU int8). Verified zero outbound network sockets in testing. | Cloud STT & LLM Pipeline. Dictation audio is transmitted to remote cloud infrastructure. | Absolute local processing guarantee. (Note: Offline execution eliminates network egress, but enterprise regulatory compliance depends on complete administrative controls, not software alone). |
| **Process Model & Memory** | FlowPilot observed at **75.8 MB RSS** baseline across 2 observed processes before model load; reaches ~280 MB after model load. | Multi-process Electron/Node.js tree observed at **1,286.2 MB RSS** across 12 child processes. | Snapshot observation via `psutil`. FlowPilot was observed across 2 processes in this measurement. Wispr Flow process tree was observed running on host. |
| **Transcription & Formatting Latency** | **p50 = 561.1 ms, p95 = 999.0 ms** (transcription + formatting processing duration on CPU). | Vendor claims ~400–1,200 ms depending on network round-trip and server load. | Note: Measured from audio WAV buffer delivery through STT inference and ContextProcessor formatting. Visible-text insertion timing is measured separately in desktop insertion suites (headless runs safely returned `FAILED_RECOVERY_AVAILABLE` without a target window). |
| **Formatting & FactGuard** | Local deterministic rules (FactGuard) protecting numbers, dates, and negations without external LLM calls. | Remote cloud LLM reformatting with active-window context awareness. | On a 15-phrase synthetic SAPI corpus, raw Whisper scored 21.26% WER against spoken reference vs 12.18% post-formatting against cleaned reference text (differences reflect formatting/reference alignment, not halved recognition errors). |
| **Developer Identifier Handling** | Preserved 15/16 technical tokens (`Kubernetes`, `Docker`, `SHA-256`, `FastAPI`, etc.) on synthetic test corpus (93.8% accuracy). | Cloud dictionary and context matching. | Technical glossary biasing via LanguageRegistry. |
| **Meeting Intelligence** | Local **MeetingDeliberationEngine** (heuristic weighing matrix, risk radar, catch-up preview, action cards). | Cloud Notetaker (bot-free system audio capture with remote LLM summaries). | Both systems capture audio bot-free via loopback; FlowPilot executes all deliberation and summarization strictly on CPU without cloud egress. |
| **Real-Time Translation** | Native Faster-Whisper `task="translate"` on local CPU with 12-language tray selector. | Cloud translation pipeline. | Foreign speech translated directly to English text locally. Multilingual latency and conversational accuracy are subject to Whisper model size. |
| **OS Text Injection & Slow-App Recovery** | Win32 hierarchy tracking + adaptive slow-app buffer hold (3.5s for Slack/Teams/Notion; 5.0s for VMs) + `Shift+Alt+Z` (Paste Last) and `Shift+Alt+X` (Copy Last) recovery shortcuts. | App-specific timing (holds up to 3s in slow apps), Shift+Insert support, `Shift+Alt+Z` / `Cmd+Ctrl+V` recovery shortcuts. | FlowPilot adaptively matches Wispr's slow-app paste guidance with extended clipboard holding, relaxed keystroke dwell times, and dedicated recovery shortcuts. |
| **Data Retention** | `save_history_text: false` default on fresh profiles; configurable local purge (7, 30, 90, 365 days, or indefinite). | Cloud storage with vendor-managed retention and user deletion controls. | Dictation history is not saved by default. Meeting notes are stored in a separate local directory and can be purged on demand or by saved policy. |

---

## 2. Key Architecture Upgrades Delivered

1. **Sovereign Meeting Deliberation Engine (`engine/meeting_deliberation.py`):**
   - **Live Catch-Up Preview ("What Did I Miss?"):** Generates a multi-point recap from the rolling window (or labeled prior discussion preview if no recent segments exist).
   - **Decision Weighing Matrix:** Heuristic contrastive extraction evaluating options, pros, cons, and consensus status (`CONSENSUS_REACHED`, `OPEN_DEBATE`, `TABLED`).
   - **Risk & Blocker Radar:** Lexical severity tagging (`HIGH` vs `MEDIUM`) with actionable mitigation hints.
   - **Action Dispatcher:** Formats objective executive recap email drafts and GitHub/Jira Markdown task cards.
   - **Configurable Retention Policy:** Persisted `meeting_retention_days` in `config.json` enforced on startup and on demand.

2. **Native Local Translation (`engine/stt_engine.py` & `engine/meeting_notetaker.py`):**
   - Configures Faster-Whisper with `task="translate"`, natively mapping foreign audio to English text on CPU.

3. **Productivity Insights Engine (`engine/insights_engine.py` & `ui/insights_view.py`):**
   - Local metrics tracking Meeting Hours, Decisions Reached, Action Items Created, and Deep Work Ratio.

4. **Studio UI Integration (`ui/notetaker_view.py`):**
   - Header translation toggle (`🌐 Translate: OFF / EN`).
   - Status bar live catch-up trigger (`⚡ Catch Up`).
   - Tab 4 Guided Deliberation Studio with 1-click clipboard export for follow-up emails and task cards.
   - Dedicated "🧹 Retention Policy & Purge" modal.

5. **HUD Rendering Hardening (`ui/floating_hud.py`):**
   - Fixed companion rendering path to natively display Seedling and Nimbus original pixel art.

6. **Truthful Injection Reporting (`engine/orchestrator.py`):**
   - Explicitly flags unverified paste targets with `"Sent — unverified target (please check)"` instead of unqualified insertion confirmation.

7. **Visible Unverified Target Warning (`desktop_app.py`, `ui/tray_manager.py`, `ui/floating_hud.py`):**
   - Dispatches a visible amber notification via the system tray and floating companion (`⚠️ Sent — unverified target (please check) — Click to copy`) while suppressing celebratory success hearts.

8. **Config Profile Isolation (`engine/config.py`):**
   - Dynamically resolves configuration files via `FLOWPILOT_CONFIG_FILE` or `FLOWPILOT_CONFIG_DIR` environment variables for clean test isolation.

---

## 3. Verification Protocol & Test Results

The automated regression test harness defines **58 registered test suites**, verified with UTF-8 safe encoding:

```powershell
# Run the complete test suite
python -X utf8 tests/run_all_tests.py
```

**Verification Status:**
- Total Test Time: **147.77s** on Windows 64-bit (`master`)
- Overall Verdict: **53 passed, 5 skipped (honest non-interactive skips), 0 failed** (detailed in [docs/audit/RELIABILITY_RESULTS.md](docs/audit/RELIABILITY_RESULTS.md))
- Egress Verification: **Zero network sockets opened during dictation/transcription** (verified by `tests/test_network_egress.py`)
- Acoustic Reality & Metric Evaluation: Comprehensive ASR CER/WER metrics across English, Hindi, and Tamil documented in [docs/audit/TEST_STRATEGY.md](docs/audit/TEST_STRATEGY.md)
