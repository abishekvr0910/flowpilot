# Codex directive — 2026-10-23

From: Claude (finisher + reviewer of your left-open work). To: Codex, the agent that
authored the remediation work this cycle.

Master moved from `367185c` (your RC2 verified-hashes manifest) to `ca8944b` after
three successive commits that complete both scopes. This file records what changed,
what is proven, and the guardrails for whatever you touch next.

## What happened after your last commit, in one paragraph

Your three shelved UI defects were fixed at source with tests, your scope 20 item
(companion visibility interactive gate) had its automatable portion measured on the
real desktop, your scope 24 item (windowed video detection) was formally closed as
manual per-app rules per your research note, doc drift was reconciled, the full 54
suite strict gate passed repeatedly on the final tree, and the packaged binary that
the user actually runs was upgraded mid-session from the stale Oct 22 build to a
fresh Oct 23 build. Nothing has been pushed; all commits are local.

## Commits in this cycle (on top of your RC2 manifest commit)

- `86181d0` — the comprehensive cycle commit: both scope closures, the three UI
  fixes with tests, the gate probe and UI audit harnesses, all doc updates
  (58 files, +3798/-133).
- `62892df` — probe child tidy: removed a stray `QT_QPA_PLATFORM=""` line, a
  walrus-as-statement, and an unused `import os`.
- `ca8944b` — probe kitty parked fully offscreen (rectifying the honest mistake
  observed by the user), foreground-taker window relocated from screen center to
  the top-left corner, and stale-binary warning tripwires added to
  `tests/test_standalone_binary_smoke.py` and `tests/test_release_integrity_fixes.py`
  (3 files, +28).

## The three UI defects: memory hook

1. **Wheel over a closed combo no longer mutates its stored value.** Implementation:
   a single application-level `_ComboWheelGuard(QObject)` singleton class in
   `ui/flowpilot_dashboard.py` (module-level `_ComboWheelGuard` + global
   `_wheel_guard`), installed exactly once from `FlowPilotDashboard.__init__` via
   `_ensure_wheel_guard(QApplication.instance())`. It consumes the wheel over any
   closed `QComboBox` and retargets it to the nearest ancestor
   `QAbstractScrollArea` viewport; open popups pass through untouched. Per-instance
   filters are provably the wrong shape, where multiple test instances install
   application-level filters and stale ones consume events first (the whole reason
   `FlowPilotDashboard` never got a real `closeEvent` before that design was dropped
   in this cycle).
   The unit tests (`tests/test_workspace_refresh.py`, helper `_wheel()`, three wheel
   tests) intersect via `sendEvent` so they exercise the real filter.
2. **Insights honest empty state.** `engine/insights_engine.py` DEFAULT data now
   declares `wpm_rolling = 0.0`, `daily_streak = 0`, and the first recorded session
   seeds the WPM directly (no 150 WPM prior inside the EWMA). `get_metrics` gains
   the `has_data` field; `ui/insights_view.py` displays dashes for wpm, streak, and
   deep-work percent until real data exists. Never reintroduce fabricated defaults;
   existing profiles migrated by keep-existing-value saves.
3. **Reachability at the minimum 880x580 size.** `ui/workspace_home.py` and the
   settings general tab scroll area now keep real horizontal `ScrollBarAsNeeded`
   scrollbars instead of `ScrollBarAlwaysOff`. The UI audit (now
   `scratch/ui_audit_20261023.py`, committed) drives every page structure and
   reports min-widget geometry plus scrollbar reachability.

## Scope A outcome (your feature 20)

The automatable portion of the gate was measured with the real
`ContextMonitor` + `CompanionVisibilityController` + real `FloatingHUD` against a
separate-process third-party fullscreen window (`scratch/ws_probe_child.py`).
Recorded results live in
`docs/testing/COMPANION_VISIBILITY_INTERACTIVE_GATE_RESULTS.md`: hide 0.203s/0.516s
and restore 0.610s/0.625s against the 1s spec caps, maximized plain window holds the
companion (AC-3), and ten full context samples all complete far under the 0.25s cap
(AC-7). Two passing runs stand as the measured evidence; several runs are
honestly recorded as UNMEASURABLE while the user is actively using the desktop
(the Windows foreground handoff belongs to the foreground process only).
The human checklist portion of the gate remains open and is listed below.

## Scope B outcome (your feature 24)

Closed as manual per-app rules. No local signal can prove a visible windowed video
without reading pixels or private content. The decision rationale is in
`docs/scope/companions.md` and `docs/research/WINDOWED_VIDEO_COMPANION_DETECTION.md`;
`docs/scope/index.md` marked feature 24 closed.

## Probe discipline when you next touch it (do not regress these)

- The probe kitty stays parked offscreen (`hud.move(-20000, -20000)` right after
  construction and again after `controller.start()`). It must remain visible to Qt
  so the AC checks its show/hide flips, but must never litter the user's desktop.
  The user personally reported the on-screen flash of a second kitty as a defect.
- The probe always stages its own isolated `CompanionStore(tempdir)` and
  `FLOWPILOT_CONFIG_DIR` + `FLOWPILOT_MUTEX_NAME` + `FLOWPILOT_HEADLESS` env BEFORE
  importing engine modules (config path is captured at import time). The user's
  real `%USERPROFILE%\.flowpilot` must never be written by a harness.
- The fullscreen child must be a separate process: `window_inspector.py:149` sets
  `own_app = pid == os.getpid()`, so own-process fullscreen windows are invisible to
  the monitor, which is by design.
- Never run the probe while the user is actively typing. An unmeasurable outcome is
  honest evidence, not a failure to smooth over. Do not retry in a loop.
- Windows grants foreground handoff only from the foreground process, so the probe
  takes foreground itself before spawning the child.

## Packaging state and the footgun you must keep working

- The user's live kitty runs from `dist\FlowPilot\FlowPilot.exe`, rebuilt fresh this
  session (2026-10-23, PyInstaller spec build passed; smoke suite passed against it
  with no stale warning; the user's profile carried over, `schema_version` migrates
  1 → 2 on packed first launch).
- The packaged-launch tests now fall back to `dist\FlowPilot\FlowPilot.exe` when
  `FLOWPILOT_TEST_EXE` is unset, and both warning tripwires print a loud five-line
  warning when that binary is older than the newest source under `engine/` or
  `ui/`. Keep these tripwires; without them a stale default silently produces
  misleading verdicts (observed in this cycle: a stale exe made the Release
  Integrity suite fail on the companion migration asserts).
- Do not rebuild `dist` while FlowPilot is running (the running exe locks the
  image). Quit the tray app first, then build, then relaunch.
- The respected gate invocation for packaged suites:
  `python -X utf8 tests/run_all_tests.py --require-all` with
  `FLOWPILOT_TEST_EXE=S:\APPs\New folder\scratch\companion-visibility-build-20261022\dist\FlowPilot\FlowPilot.exe`
  (or a rebuild in the default dist location).

## Verification record at the time of this directive

- Full strict gate after every source change: 54/54 passed, 0 skipped, 0 failed.
  Timings observed: 126.77s, 128.97s (one suite failing before the root cause was
  understood, see footgun), 133.68s, 135.15s, 141.46s across the day.
- Focused suites for touched areas: `test_workspace_refresh.py` 18 passed,
  `test_insights_engine.py` 8 OK, `test_flowpilot_dashboard.py` OK,
  `test_companion_visibility.py` 16 passed.
- The RC2 release itself is untouched: `367185c` recorded your CI build's hashes
  and the RC2 archive was never modified in this cycle. None of the three post-RC2
  commits are part of a release yet.

## Release position (your most important conservative reminder)

Three commits of fixes exist AFTER your RC2 release manifest. A future release
cannot simply re-run `docs/manifest` hashing against existing artifacts; it needs a
fresh CI build of this master plus a new manifest run and the full strict gate under
`--require-all`. Treat the RC2 hashes as frozen history, not as current truth.

## Open items you inherit (do not close by assumption)

1. Human-portion of the companion visibility gate remains open in
   `docs/testing/COMPANION_VISIBILITY_INTERACTIVE_GATE.md`: Chrome F11, real
   PowerPoint or presentation mode, F9 tray behavior while hidden, third-party
   paste across real editors, packaged binary on a live session, restart
   persistence, multi-monitor sanity. These need the user, not an agent.
2. Feature 20 in `docs/scope/index.md` is still in-progress until the human portion
   above is signed. Do not flip it to closed without that evidence.
3. The remaining UI audit findings are reachability verified (scroll works) and
   style-only: several narrow buttons at default window size are snug. A padding
   trim in `ui/workspace_style.py` is proposed but explicitly NOT requested by the
   user; leave it for an explicit ask.
4. `README.md` mojibake is preexisting from an earlier encoding pass; fix reads by
   measuring the file, not trusting it.

## Room conventions you already know, restated as stop signs

- Stage env vars before any engine import (`engine/config.py` captures the config
  path at import time).
- Every subprocess passes `encoding="utf-8", errors="replace"` and children run
  with `-X utf8`.
- Zero cloud egress stays intact; `test_network_egress.py` applies to any new
  engine call.
- Truthful status: never report paste as succeeded unless the target window was
  really verified; InjectionStatus wording drives the UI.
- Route companion show/hide exclusively through `CompanionVisibilityController`.
- Local commits only; nothing leaves this machine without an explicit user request.
- Test isolation is env-based (`FLOWPILOT_CONFIG_FILE`, `FLOWPILOT_CONFIG_DIR`,
  `FLOWPILOT_MUTEX_NAME`, `FLOWPILOT_HEADLESS`); unique mutex name per PID for
  suites that spin the whole app.
- Never terminate desktop processes by generic name; ask before killing anything
  the user is actively using, including their running FlowPilot kitty.

## Later same-day update, source after `b67c9b9`

This directive records the state at `ca8944b`. Two later local commits added a
competitor artifact research note (`e01eb85`) and an approximate audible-media
companion feature (`b67c9b9`). The current working tree also contains uncommitted
fixes for that feature. Read [the media validation note](../testing/MEDIA_AUDIO_PRESENCE_VALIDATION_2026-10-23.md)
before treating this older packaging and test record as current.

The media fix resets its sustain latch after quiet, reads session mute, and runs
Windows audio-session queries off the Qt thread. Its isolated development binary
passed smoke and offline self-test. The final isolated suite recorded 49 passed,
5 skipped, 0 failed across 54 suites; `npm test` passed. The five skips and the
unperformed live video and presentation trials keep release promotion open. RC2
and the default `dist/FlowPilot` executable were not replaced by this work.
