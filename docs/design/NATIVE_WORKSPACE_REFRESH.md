# Native workspace refresh

Status: implemented in source; focused verification passed (Codex UI track).

## Scope and ownership

Refresh the native PySide6 Home, Companion Studio and Settings experience. Preserve
existing engine, hotkey, clipboard, renderer and storage contracts. Gemini owns the
physical desktop test corrections; this track must not edit those test files.
No release build, commit, push, cloud service or new runtime dependency is required.

## Design

A warm Sand & Stone light workspace by default, with an Obsidian dark option,
consistent type and control spacing, grouped navigation, and an original companion
as the playful element. Home prioritizes the
configured shortcut, language/model, last-result recovery and a companion preview.
Settings and Studio open inside the dashboard; standalone tray dialogs still work.
Keep all existing tools accessible. Do not claim model/microphone readiness merely
because a configuration value exists. Clearly label simulated companion states.

## Acceptance checks

- Home shows the actual shortcut (including F9) and reflects saved settings.
- No model load, microphone acquisition or injection just by opening these pages.
- Studio uses existing assets/renderer, preserves draft Apply/Cancel semantics,
  exposes unverified/recovery previews, and honors reduced motion.
- Settings retains validation, shared personalization and save-failure feedback.
- Existing navigation and recovery actions remain wired to production handlers.
- Render the three views at normal and small supported window sizes in an isolated
  profile. Check readable text, scrolling, keyboard focus and no clipped actions.
- Run focused UI/behavior tests; record the broader gate honestly, without forcing
  physical desktop tests or changing Gemini's work.

## Implementation

- `ui/workspace_style.py`: shared native Sand & Stone/Obsidian styling and typography.
- `ui/workspace_home.py`: configured shortcut/language/model, session recovery,
  honest retention wording and selected-companion preview. No inferred readiness.
- `ui/flowpilot_dashboard.py`: grouped, scrollable navigation; embedded Studio and
  Settings while retaining all existing tools. Failed settings updates are not saved.
- `ui/companion_studio.py`: searchable rendered character tiles, explicitly simulated
  state previews including unverified/recovery, Apply/Cancel and complete HUD settings
  delivery through `desktop_app.py`. Standalone tray dialogs remain supported.
- `ui/settings_dialog.py`: scrollable dictation form, shared personalization, embedded
  save feedback and retained shortcut-conflict validation.
- `ui/companion_preview.py`: hidden/reduced-motion previews do not run animation timers.

## Verification and handoff

- 105 focused tests passed across workspace, dashboard, Settings, Studio, pixel creator,
  Kiki, integration safeguards and voice-command/LLM suites. One existing pytest warning
  concerns the Settings test returning a boolean instead of `None`.
- Added workspace tests and registered their module in `tests/run_all_tests.py`.
  The runner now lists 49 suites; this is not a claim that all 49 were executed.
- Rendered real Qt screenshots at 1160×820 and 880×580; checked Home, Library and
  Dictation Settings for layout, scrolling and footer visibility.
- Reproduce without user data or microphone access:
  `python scripts/preview_workspace.py --output scratch/workspace-preview`
- Sand & Stone is the default native theme; Obsidian is selectable in Settings.
  Home, Studio, Settings, Scratchpad and Meetings were visually checked at normal
  and compact sizes. Legacy tools receive shared color harmonization; Meetings
  now uses Library/Live transcript/Notes tabs to avoid clipped recording controls.
  Full keyboard/screen-reader and real-display visual acceptance remain pending.
- No production engine changes, commit or push. During integration review, a
  copied competitor WebEngine renderer and credential-reading bridge were removed
  from runtime and quarantined under ignored `scratch/`. The native dashboard
  remains the only desktop Home implementation. A new local unpacked binary was
  built and smoke-tested, but the existing RC1 ZIP was not regenerated or released.
- The combined 49-suite source gate passed on the interactive desktop with no
  skips; the earlier attempt exposed intermittent first-pass Notepad insertion.
  The harness now distinguishes a proven-absent recovery retry from first-pass
  delivery, so a green gate is not a 99.9% first-attempt reliability claim.
