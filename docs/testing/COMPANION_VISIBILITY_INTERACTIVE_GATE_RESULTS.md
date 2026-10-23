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
- This earlier probe did not touch browsers, slide shows, the real tray,
  dictation flows, or a packaged binary. Its open items were subsequently
  narrowed by the live packaged checks below. Restart persistence, Studio
  app rule changes, reduced motion, and a broader editor pilot remain open.

## Automated suite status on the same day

`python -X utf8 tests/run_all_tests.py --require-all` with `FLOWPILOT_TEST_EXE` pointing at `scratch/companion-visibility-build-20261022/dist/FlowPilot/FlowPilot.exe`: 54 suites, 54 passed, 0 skipped, 0 failed, 133.68 s total (an independent strict rerun earlier the same day measured 135.15 s). The packaged smoke suite runs inside that count against the hash verified dev build.

## Later packaged live gate

The repaired candidate executable was tested on the unlocked desktop on
23 October 2026. Its SHA-256 is
`D17FEC1C94918520CAF51B3F250897875671B6BB0B401429315AA08999ABF52E`.
Audible and muted windowed media, browser F11, a real PowerPoint slide show,
F9 dictation while Hidden, and mixed DPI frame fit passed with measured
observations in [the media validation note](MEDIA_AUDIO_PRESENCE_VALIDATION_2026-10-23.md).
The first F9 attempt lost foreground to Chrome and was not counted; the
repeat verified the text in Notepad. The strict runner on this exact package
reported 54 passed, 0 skipped, 0 failed in 175.07 s.
