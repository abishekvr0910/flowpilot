# Companion visibility interactive gate, measured results

Companion to [the interactive gate checklist](COMPANION_VISIBILITY_INTERACTIVE_GATE.md). Recorded 23 October 2026. RC2 stays unchanged; this is development build work after RC2.

## Automated live desktop probe, PASSED twice

Tool: `scratch/gate_probe_20261023.py` with `scratch/ws_probe_child.py`. The probe drives the real `FloatingHUD`, the real `CompanionVisibilityController`, and the real `ContextMonitor` in one live session, so fullscreen classification and shell state come from the actual desktop, not monkeypatched calls. The fullscreen window belongs to a separate child process because `engine/window_inspector.py` ignores windows owned by the app itself when deciding the context (`own_app = pid == os.getpid()`), which mirrors the real third party case.

Isolated env per run: fresh `FLOWPILOT_CONFIG_DIR` in a temp directory plus a distinct single instance mutex, so the user profile and the user's daemon were untouched.

Measured pass criteria were fixed before the runs, from spec 0001:

- AC-2 the companion hides within one second of borderless fullscreen and returns within one second of leaving it.
- AC-3 a bordered maximized plain window is not treated as fullscreen and keeps the companion visible.
- AC-7 one complete `ContextMonitor.sample()` finishes under 0.25 s.

| Metric | Run 1 | Run 2 | Spec limit | Verdict |
|---|---|---|---|---|
| Fullscreen hide latency | 0.516 s | 0.203 s | ≤ 1 s | PASS |
| Restore latency | 0.610 s | 0.625 s | ≤ 1 s | PASS |
| Hide basis | not recorded by that run | monitor classification `fullscreen=True`, shell state 5, separate process | third party window | PASS (run 2) |
| Maximized plain window held the companion | yes | yes | no false hide | PASS |
| Full context sample duration | under 1 microsecond each of ten samples | same | ≤ 0.25 s | PASS |

Run context recorded at the moment of hiding: foreground classified as borderless fullscreen (`fullscreen=True`), shell notification state 5, foreground process a third party python child window, so the hide came from the fullscreen policy rather than Windows presentation state or an app rule.

Latency scales with the controller interval: `ui/companion_visibility_controller.py` polls at 350 ms and requires two stable samples, which explains 0.203 s to 0.63 s measured transitions. Both sit inside the one second limit with margin.

## Probe limitations

- The probe reports unmeasurable instead of a pass when the operator keeps working, because a fullscreen child window depends on Windows foreground handoff, and any foreground activity can win it back. Attempted runs while the user was active produced this honest unmeasurable outcome rather than a false pass.
- The probe does not touch browsers, slide shows, the real tray, dictation flows, or the packaged binary. Every human row in the checklist remains open: Chrome F11, real PowerPoint or Windows presentation mode, F9 while hidden, third party paste behavior in real editors, restart persistence of Hide and Always show, app rule behavior through Studio, motion and focus behavior, and ordinary windowed browser video (this build does not recognize it by design; use a manual app rule).

## Automated suite status on the same day

`python -X utf8 tests/run_all_tests.py --require-all` with `FLOWPILOT_TEST_EXE` pointing at `scratch/companion-visibility-build-20261022/dist/FlowPilot/FlowPilot.exe`: 54 suites, 54 passed, 0 skipped, 0 failed, 133.68 s total (an independent strict rerun earlier the same day measured 135.15 s). The packaged smoke suite runs inside that count against the hash verified dev build.
