# 0001. Context aware companion visibility

**Date:** 2026-10-22  
**Status:** In Progress  
**Audience:** Gemini implementation partner and FlowPilot maintainers  
**Baseline:** local commit `367185c`, tagged `v3.1.0-RC2`

## Summary

Let the companion step aside when it would interrupt a video, presentation, or coding session. Keep dictation working and show its true status in the system tray even when the companion is hidden. Build one native visibility policy around the existing Qt HUD and user settings, then add app rules and optional suggestions. This is the active implementation contract, not a claim that the feature exists in RC2.

## Context

> ⚠️ Premise note: A browser process or a playing media session does not prove that the foreground window contains a video. Hiding the pet whenever Chrome plays audio would also hide it while someone works with music in the background. The first version should use fullscreen and presentation signals, plus explicit app rules. Reliable windowed video recognition needs a separate proof before release.

The HUD currently starts visible in `desktop_app.py:171`, even though `engine/companion_store.py` has a `visible` setting. The tray can toggle the HUD, but several other paths call `hud.show()` directly. `ui/floating_hud.py` starts a 33 ms animation timer at construction and continues calling `update()` while hidden. `ui/companion_preview.py` already stops its timer when hidden, so the live HUD can use that pattern.

`engine/preference_learning.py` stores deliberate settings observations and approved app rules with opt in consent. Studio can display and approve those rules, but no runtime code currently applies them to companion visibility. This plan must connect that last step rather than claim the learning feature already controls the pet.

The existing architecture requires native PySide6 rendering, no focus theft, no cloud egress, and truthful recording and paste status. RC2 source and CI checks are green, but the candidate is unsigned and held for pilot validation. This work belongs in a new candidate after RC2, not silently inside its existing archive or hash manifest.

## Requirements

**User stories**:

- As a viewer, I want the companion to disappear during fullscreen video or a presentation so it does not cover content.
- As a developer, I want a small, quiet presence in my chosen editor or terminal while F9 dictation still works.
- As a user, I want to choose when the companion stays visible and to reject any suggested rule.

**Acceptance criteria**:

- **AC-1:** Global `Smart`, `Always show`, and `Hide` choices work at startup and after restart. Old `visible` values migrate without discarding the selected character, position, motion, or sound settings.
- **AC-2:** In `Smart`, a foreground fullscreen app or Windows presentation mode hides the companion within a measured target of one second. Leaving that state restores the correct prior presentation within one second when the user did not choose `Hide`.
- **AC-3:** A normal maximized editor must not be treated as fullscreen. Transient `GetForegroundWindow() == 0`, failed Windows calls, multiple monitors, and rapid focus changes must not make the HUD flash or appear over a known fullscreen window.
- **AC-4:** In `Smart`, a user can choose `Normal`, `Edge`, or `Hidden` per foreground app. Editor and terminal quiet defaults may use `Edge`, but must not change the saved companion asset. A user rule wins over those defaults.
- **AC-5:** The tray and dashboard can show the effective mode and its reason, let the user choose a persistent mode, and provide a temporary `Show now` override. All show and hide paths use one controller. No caller bypasses the policy with direct `hud.show()`.
- **AC-6:** Hiding the HUD never stops recording, changes the F9 hotkey, changes microphone ownership, changes injection targeting, or converts `SENT_UNVERIFIED` into confirmed success. While hidden, the tray still shows listening, processing, success, unverified, and recoverable failure states.
- **AC-7:** A hidden or static HUD stops its 33 ms animation timer. It restarts only when visible motion needs it. Reduced motion stays static in every presentation mode. Context checks must not cause perceptible Qt UI stalls; measure their duration and move slow calls off the GUI thread if needed.
- **AC-8:** Studio offers accessible visibility controls and app rules. The user can restore a hidden pet from the tray without reopening Studio, and can undo a rule without losing the chosen character or position.
- **AC-9:** Suggestions use only deliberate manual visibility choices after explicit learning consent. The existing three distinct day and 80 percent rule is retained. Auto hides never count as a user choice. Proposals require acceptance and a rejected rule does not immediately reappear.
- **AC-10:** Context detection reads only local window identity, geometry, and Windows presentation state. It never reads screen pixels, keystrokes, clipboard text, window titles, URLs, project files, or transcripts, and causes no non loopback network call.
- **AC-11:** Unit, Qt, Windows interactive, packaging, and offline tests report passes and skips honestly. The new feature cannot be called complete from a headless CI pass alone.

## Options considered

### Option 1: Add more show and hide calls to the HUD

This can cover fullscreen quickly with little new code. It leaves the current direct calls competing with manual controls and makes restore behavior hard to reason about.

**Pros:** Small initial diff.

**Cons:** Conflicting callers can reshow a hidden pet, and the existing `visible` setting remains unreliable.

### Option 2: One native visibility controller

A small QObject receives local context, user intent, approved app rules, and the engine state. It computes one presentation state and is the only production path that shows or hides the HUD.

**Pros:** Predictable priority, focused tests, no new process or socket bridge.

**Cons:** Existing dashboard, Studio, and tray calls must be rewired together.

### Option 3: Browser and IDE extensions first

Extensions could report page or workspace context with more detail. They add permissions, distribution, and security review before the basic desktop behavior works.

**Pros:** Potentially more precise context in supported hosts.

**Cons:** Does not cover VLC, PowerPoint, other editors, or the current manual visibility defect.

## Decision

**Chosen option:** Option 2, one native visibility controller.

Use the existing Qt event loop, Win32 window metadata, `CompanionStore`, `PreferenceLearningEngine`, and tray state. Treat a VS Code status item and windowed media detection as separate later decisions. No Electron renderer, screen capture, global typing hook, or new network service is part of this feature.

## Rationale

One policy owner solves the existing startup and manual toggle inconsistency before introducing automatic behavior. A bounded Qt context check is easier to test and maintain than a global hook at this scale. A first pass can reliably cover presentation and plausible fullscreen cases while admitting uncertainty about windowed browser video.

## Feature design

### Data model sketch

| Record | Key fields | Source and rule |
|---|---|---|
| Global companion choice | `visibility_mode: smart | always | hidden`, `last_visible_mode: smart | always` | `companion.json` through `CompanionStore`; migrate old `visible: true` to `always` and `false` to `hidden` for existing profiles. New profiles default to `smart`. Preserve every other companion field. |
| Approved app choice | normalized executable name, `companion_visibility: normal | edge | hidden` | Existing `learning.json.approved_rules`; manually approved rules remain active when learning is later turned off. Reject unsupported values. |
| Learning observation | app name, setting key, chosen value, local calendar day | Existing opt in `learning.json.observations`; record only explicit actions when not in automatic fullscreen suppression. Keep the current retention and tombstone behavior. |
| Context snapshot | foreground HWND, executable basename, monitor, fullscreen classification, shell notification state, sample time | Memory only. Never persist the HWND, window title, path, or media metadata. |
| Effective presentation | `normal | edge | hidden`, reason, temporary override | Memory only. Derive from global choice, context, app rule, and engine state. Never save this as user intent. |

No relational database or external schema is needed. The JSON migration must be additive and idempotent. Inspect the raw saved schema and `visible` value before merging new defaults, or an old profile could be mistaken for a new one. Keep `visible` readable for legacy profiles until all callers use `visibility_mode`; do not use both as competing runtime authorities. When the user selects `Hide`, retain the prior `smart` or `always` value in `last_visible_mode` so a later tray toggle restores what they chose.

### State transitions and priority

1. `Hide` means hidden everywhere until the user changes it. `Always show` means normal presentation everywhere, including fullscreen, because it is explicit user intent.
2. A temporary `Show now` override applies only when `Smart` hid the pet. It wins for the current foreground window, expires on the next real foreground change or app exit, and is never persisted. When global `Hide` is selected, the tray instead offers `Show companion`, which restores `last_visible_mode`.
3. Under `Smart`, fullscreen or presentation state means hidden. This also wins over a normal app rule. The tray remains active.
4. Under `Smart` outside fullscreen, an approved app rule applies. Otherwise use a conservative built in quiet default for verified terminal and editor processes. Unknown apps remain normal.
5. The dictation state changes the tray icon and any visible presentation, but never changes global visibility intent. A hidden companion does not suddenly pop up when recording begins.
6. Require stable context samples or a short debounce before changing presentation. If foreground identity becomes temporarily unknown, keep the last stable presentation briefly rather than flashing over video. A lasting unknown state falls back to the user choice and shell state, not a guessed app.

Use process identity only for appearance policy. Never treat it as authorization for text injection. A full screen on any monitor may hide the pet globally in the first version, which should be called out in settings so multi monitor users understand it.

### Local interfaces and value sourcing

| Surface | Input | Output or effect | Failure behavior |
|---|---|---|---|
| `ContextMonitor.sample()` | Foreground HWND and Win32 shell state | `ContextSnapshot` on the Qt thread | Returns an `unknown` snapshot; never reads content or blocks the GUI. |
| `CompanionVisibilityController.evaluate()` | Global mode, snapshot, app rule, temporary override | `normal`, `edge`, or `hidden` plus a reason | Invalid rule becomes no rule and is logged without private content. |
| `CompanionVisibilityController.apply()` | Effective presentation | Exactly one HUD show, hide, or edge update | Idempotent, no activation or dictation side effect. |
| Tray and Studio actions | Explicit user selection | Persisted global or app choice, or temporary override | Clear failure message if persistence fails; keep prior working choice. |
| Learning proposal | Deliberate setting actions | Review card only | No proposal when disabled; dismiss or tombstone stops resurfacing. |

| Value produced or displayed | Named source |
|---|---|
| Current companion style and position | `CompanionStore` existing asset and placement fields. |
| Global choice label | `CompanionStore.visibility_mode`. |
| Effective state and reason | Controller decision from current snapshot, global choice, approved rule, and override. |
| App name shown in rule UI | Executable basename only from the foreground process. |
| Fullscreen classification | `SHQueryUserNotificationState`, foreground window bounds, and bounds of the monitor returned by `MonitorFromWindow`. |
| Listening and paste result | Existing `StateBridge` payload and `TrayManager.set_state`, never inferred from visibility. |
| Suggested rule and consensus | Existing `PreferenceLearningEngine.get_proposals()` on deliberate observations. |

### Implementation limits

Use a bounded Qt timer, initially around 250 to 500 ms, to inspect only foreground window metadata. Fullscreen changes can occur without a new foreground event, so a foreground hook alone is insufficient. Classify using Windows notification state and monitor geometry; confirm normal maximized windows separately in tests. Do not call UI Automation, inspect browser tabs, or read media titles for this feature. If sampling cost or transition time fails measurement, evaluate a WinEvent foreground hook as a later optimization with a pinned callback and clean unhook lifecycle.

`FloatingHUD` should expose a small presentation method and stop its animation timer in `hideEvent`. `showEvent` restarts only if the chosen asset and motion need animation. An `Edge` presentation uses the existing native minimal renderer without changing `selected_asset_id`, `appearance_locked`, or stored coordinates. Keep `Qt.WindowDoesNotAcceptFocus` and `WS_EX_NOACTIVATE` on every transition.

`desktop_app.py` owns the controller and routes the tray toggle, dashboard show request, Studio apply request, startup restore, and shutdown through it. The controller listens to `StateBridge` for dictation status; engine worker threads never touch widgets directly. Read approved app rules as defensive snapshots under the existing learning lock so UI updates and policy evaluation do not share mutable nested dictionaries. No changes to the STT, FactGuard, audio, or injector pipeline are needed.

Suggested file ownership: put the pure decision function in `engine/companion_visibility.py`, extend `engine/window_inspector.py` for bounded Win32 metadata, and keep the QObject that applies decisions in `ui/companion_visibility_controller.py`. Add focused tests in `tests/test_companion_visibility.py` and list that suite in `tests/run_all_tests.py`. Keep `floating_hud.py`, `desktop_app.py`, Studio, and tray changes limited to their existing responsibilities. Verify that PyInstaller finds any new module before packaging.

### Security and privacy

The only persisted context is the executable basename already needed for an approved app rule and the deliberate choice that the user made. Learning stays disabled by default. No global keyboard monitor, window title capture, source file read, browser URL, audio retention, screen pixels, or external request is allowed. Do not import Wispr Flow renderer code, bundles, graphics, or credentials; this must remain original native FlowPilot work. The tray must continue to indicate live recording while the pet is hidden. This feature does not establish HIPAA, GDPR, or any other regulatory certification.

### Critical test scenarios

- First launch and migrated profile honor `Smart`, `Always show`, and `Hide`, with exact character settings intact, verifying **AC-1**.
- Browser fullscreen, a video player, and presentation mode hide and restore within the measured target, verifying **AC-2**.
- Maximized VS Code, transient HWND zero, a second monitor, and rapid Alt Tab changes do not create false hides or flashes, verifying **AC-3**.
- App rule `edge` for `code.exe` and `hidden` for a terminal changes only presentation, not asset choice, verifying **AC-4**.
- Dashboard, tray, Studio, and restart all route through the controller, verifying **AC-5** and **AC-8**.
- Record with F9 while fullscreen and while hidden by an app rule. Tray state remains truthful and the injected text is still verified or marked unverified by the existing pipeline, verifying **AC-6**.
- Hidden and reduced motion HUD have an inactive animation timer; showing an animated pet restarts it once, verifying **AC-7**.
- Auto hide creates no learning observation. Three separate days of deliberate choices can propose one rule, but never apply it until accepted, verifying **AC-9**.
- Instrument sockets and forbidden context reads, verifying **AC-10**. Run a focused suite, the master runner, standalone smoke, and physical desktop checks with honest skip accounting, verifying **AC-11**.

## Build plan

Use one narrow end to end thread first. Keep each change reviewable and attach test evidence to it.

1. **Baseline and branch:** start from `367185c` or a newer verified descendant, not stale `origin/master`. Record `git status`, test counts, and the exact baseline. Preserve the existing untracked `AGENTS.md` and `CLAUDE.md` files. Add a pure policy test for one fullscreen transition before changing live UI. Satisfies **AC-2**, **AC-3**, and **AC-11**.
2. **Persisted intent and one owner:** add an idempotent `CompanionStore` migration, a small pure policy module, and a Qt visibility controller. Route startup and every existing direct `hud.show()` or `hud.hide()` path through it. Prove one fullscreen entry and exit in a test and on the interactive desktop. Satisfies **AC-1**, **AC-2**, **AC-3**, and **AC-5**.
3. **Quiet presentation and lifecycle:** add `Edge` as a temporary presentation of the saved asset, wire tray status from existing `StateBridge`, and pause hidden or static HUD animation. Test F9, focus integrity, reduced motion, and unverified paste messaging. Satisfies **AC-4**, **AC-6**, and **AC-7**.
4. **User controls and local proposals:** add global mode and per app controls to Studio and tray. Connect approved rules to the controller and deliberate choices to `PreferenceLearningEngine`. Test accepted, rejected, forgotten, disabled, and restarted states. Satisfies **AC-5**, **AC-8**, **AC-9**, and **AC-10**.
5. **Verification and release decision:** add focused unit and Qt suites, run the full regression runner with honest skips, physical fullscreen and editor trials on the interactive desktop, network egress checks, and a packaged offline smoke test. Measure transition time, false hides, focus changes, and idle CPU before and after. Do not reuse the RC2 archive hash or publish a new release until these gates and human pilot review pass. Satisfies **AC-2**, **AC-3**, **AC-6**, **AC-7**, **AC-10**, and **AC-11**.

Gemini should report each PR with changed files, tests added, command output, skips, measured behavior, open risks, and any deviation from this proposed decision. Do not substitute a green unit test for an interactive fullscreen test. Do not commit, push, retag RC2, or publish an artifact merely because this directive exists.

## Migration plan

**Strategy:** Introduce the new controller alongside the current HUD rendering, then route callers to it one by one within the same feature branch. Keep the old `visible` field readable for existing profiles during migration.

**Phases:**

1. Parse old profile data before merging new defaults, add `visibility_mode` and `last_visible_mode`, and prove repeated loads produce the same result.
2. Route startup, tray, dashboard, and Studio visibility actions through the controller. Only then enable automatic fullscreen decisions under `Smart`.
3. Add app rules and suggestions after the single owner is exercised by focused and interactive tests.

**Rollback:** Revert the feature branch or disable the new controller before a release. Older code can ignore the additive JSON fields; it will lose the new visibility behavior but must retain the saved character and placement. Never roll back by deleting a user's `companion.json` or `learning.json`.

**Risks:** An old profile with `visible: false` was not honored at startup before this change, so honoring it after migration may surprise that user. Test and document that correction. A direct caller left behind can override the controller and must be found by source search plus tests.

## Consequences

**Positive:** The character feels considerate, the user's explicit choice remains authoritative, and hidden animation uses less work.

**Negative:** Fullscreen classification can be imperfect across Windows apps and displays. More UI states and a small persistent migration add test burden.

**Neutral:** This plan does not promise automatic detection of every windowed video or an in editor character. Those are separate decisions after the first slice is measured.

## Follow-up

- [x] Measured on a live desktop session, 23 October 2026: borderless fullscreen hide 0.203 s and 0.516 s, restore 0.610 s and 0.625 s, maximized plain window holds the companion, full context sample under one millisecond per call, and 54/54 automated suites green on the same day. See [the gate results note](../testing/COMPANION_VISIBILITY_INTERACTIVE_GATE_RESULTS.md). The human portion of the gate note stays open.
- [ ] Decide whether active fullscreen recording should use tray status only or also a tiny edge indicator. Tray only is the proposed default, pending user confirmation.
- [ ] Design the optional VS Code status item separately. Keep it opt in, local, and free of source or workspace text by default.
- [x] Windowed media closed as manual app rules: the research note finds no provable local signal without reading pixels or private content. See [the research note](../research/WINDOWED_VIDEO_COMPANION_DETECTION.md) and the scope entry.
- [ ] Explore screen capture exclusion separately. It is not the same as hiding the companion on the user's display and is not a security guarantee.

## References

**Project sources:** `desktop_app.py`, `ui/floating_hud.py`, `ui/companion_preview.py`, `ui/tray_manager.py`, `engine/companion_store.py`, `engine/preference_learning.py`, `docs/release/RELEASE_ARTIFACT_MANIFEST.md`.

**Practices and standards:** One owner for visible state, explicit user override, conservative classification under uncertainty, and honest physical desktop testing.

**Links:**

- [Windows notification and presentation states](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/ne-shellapi-query_user_notification_state)
- [Windows foreground event hook contract](https://learn.microsoft.com/en-us/windows/win32/winauto/event-constants)
- [Window to monitor mapping](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-monitorfromwindow)
- [Qt focus avoiding window flag](https://doc.qt.io/qt-6.12/qt.html)
- [VS Code status bar guidance](https://code.visualstudio.com/api/ux-guidelines/status-bar)
- [Windows capture exclusion and limitations](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity)
- [Wispr Flow Bar behavior for comparison](https://docs.wisprflow.ai/articles/1790396454-move-and-dock-the-flow-bar-on-desktop)
