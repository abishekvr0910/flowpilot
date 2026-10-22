# FlowPilot Engineering Directive

**Applies to:** current `master` source and future changes. **Last revised:** 2026-10-19. This is a project policy, not a certification that every target has already been met. The [original October 16 directive](../archive/CODEX_DIRECTIVE_2026-10-16.md) is preserved as a historical snapshot.

## Product boundaries

1. **Local-first speech processing.** Whisper and VAD inference run on the user's machine. Cloud STT branches remain disabled. The optional REST/WebSocket bridge is for loopback integrations, not desktop UI rendering; native PySide6 owns the visual experience. New network paths require explicit review and egress tests.
2. **Honest local data handling.** New profiles default to `save_history_text: false`; completed-dictation persistence is bypassed until the user opts in. Existing profile settings, older saved entries, meeting notes, and scratchpad storage have separate lifecycles. Changes to retention, deletion, or defaults must update [PRIVACY.md](../../PRIVACY.md), UI disclosure, and regression tests together. Do not log raw speech or transcripts to diagnostics.
3. **First-syllable protection.** Maintain the 350 ms warm pre-roll buffer and test the hotkey-to-capture transition. Treat zero clipping as a design objective, not a universal guarantee without hardware evidence.
4. **Focus integrity.** The passive HUD must not activate or steal editor focus. Intentional settings and Studio windows may accept focus when the user opens them; restore the prior workflow safely. Test real target applications, not only mock controls.
5. **Meaning preservation.** Deterministic formatting must guard negations, amounts, dates, and developer identifiers. On ambiguity or failed verification, prefer the raw transcription and make uncertainty visible.
6. **Lifecycle safety.** Enforce one desktop microphone owner, avoid blocking duplicate-instance popups, and release audio, hotkey, and window resources on quit or failure.
7. **Sovereign Meeting Deliberation & Intelligence.** Meeting summaries, live catch-up ("What Did I Miss?"), decision weighing matrices (pros/cons), risk & blocker radar, and action card generation run purely local on CPU without external LLM calls or cloud telemetry. Real-time translation to English executes strictly via Faster-Whisper `task="translate"` on the local device. Granular retention policies (7, 30, 90, 365 days) physically purge local files on schedule without network synchronization.
8. **No invented performance or compliance status.** Benchmark claims need hardware, corpus, sample size, metric definition, date, and source commit. Legal or security certifications require their own evidence and review.

## Verification gate

The current [runner](../../tests/run_all_tests.py) defines 53 suites (2026-10-22). Run `python -X utf8 tests/run_all_tests.py --require-all` for release candidates and inspect [live CI](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml) before publishing a build. Hardware checks skipped in headless CI remain unverified; they need explicit Windows hardware validation. A failed or skipped strict gate blocks release promotion. Do not relabel skipped or failed suites as passes, and do not reuse older release results for newer source.

Published artifacts are listed in [GitHub Releases](https://github.com/abishekvr0910/flowpilot/releases). The dated [v3.0.2 report](../release/FLOWPILOT_V302_RELEASE_REPORT.md) applies only to that release. The [benchmark protocol](../testing/FLOWPILOT_BENCHMARK_PROTOCOL.md) describes how new measurements should be reported.
