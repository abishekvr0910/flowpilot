# UI

## Overview

PySide6 windows for the whole desktop experience: dashboard, tray, floating companion HUD, setup wizard, settings, and feature hubs, plus the flat web companion served at 127.0.0.1:8765. Engine callbacks reach windows only through `StateBridge` Qt signals.

## Key files

| File | Owns |
|---|---|
| floating_hud.py | Always on top companion HUD, `WS_EX_NOACTIVATE` through ctypes, no keyboard focus ever |
| companion_visibility_controller.py | Sole runtime owner of HUD show, hide and quiet edge presentation under spec 0001 |
| tray_manager.py | Tray icon, menu, notifications, signal fan out for toggles |
| flowpilot_dashboard.py | Main window that holds the hub views |
| notetaker_view.py | Meeting tabs, translation toggle, catch up and deliberation controls |
| scratchpad_view.py | Scratchpad hub, one of five feature hubs alongside transforms, dictionary, snippets, history, and insights views |
| companion_renderer.py, pet_sprites.py, pixel_creator.py, companion_studio.py, companion_preview.py | Mascot rendering, sprite states, painting and preview stack |
| setup_wizard.py, settings_dialog.py | First run flow and device or hotkey settings |
| index.html, app.js, styles.css | Flat web companion served by `engine/server.py` |

## Conventions

- Engine threads reach widgets only through `StateBridge.state_changed`; never poll engine objects from a dashboard timer.
- The HUD never takes keyboard focus; keep the `WS_EX_NOACTIVATE` setup and the ctypes native font picks intact.
- Route companion show and hide actions through CompanionVisibilityController. Do not call HUD show or hide from dashboard, tray, or Studio.
- Keep slow Windows audio session sampling off the Qt thread. The visibility controller reads the cached media signal and starts or stops its sampler with the HUD lifecycle.
- Feature hubs are widgets appended in the dashboard; when adding one, keep the tray menu and hotkeys in sync.
- The external transform panel supports preview and explicit Copy Output. Replace and Revert stay disabled; successful formatting does not authorize an external edit or prove delivery.
- Web companion is same origin only; the server whitelists 127.0.0.1 ports, do not widen it.

## Gotchas

- `desktop_app.py` mutates private FloatingHUD attributes directly for companion styles (`_visual_style`, `_cat_palette`, `_cat_pixmap_cache`, `_motion_preset`); renaming those attributes breaks that wiring.
- Four files sit above 800 lines (`pet_sprites.py` 1480, `companion_renderer.py` 1460, `pixel_creator.py` 1042, `notetaker_view.py` 1033); `floating_hud.py` (759) is under the cap. Add to big files sparingly, prefer new modules.
- `README.md` holds mojibake from an earlier encoding pass; fix reads by measuring the file, not trusting it.

## Related specs

None yet.

_Drafted by /audit from the repo, worth a quick human pass. Edit freely: once a line stops matching this draft, later runs treat it as curated and will flag rather than overwrite it._
