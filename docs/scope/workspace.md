# Workspace

The workspace should make the core voice journey understandable and calm. New panels do not help if users cannot find the microphone, recover text, or leave a failed view.

## Existing foundation

### 7. Setup, settings, and dashboard · existing

A first run setup flow, settings, and the main dashboard are implemented. Code in `ui/setup_wizard.py`, `ui/settings_dialog.py`, `ui/flowpilot_dashboard.py`, and `desktop_app.py`.

### 8. Scratchpad, history, and insights · existing

The app has a scratchpad, an opt in dictation vault, selected text transform previews with Copy Output, and productivity views. External Replace and Revert are unavailable in current source; scratchpad editing has its own guarded transactions. Retention choices and recovery buffers have different lifecycles. Code in `ui/scratchpad_view.py`, `ui/transforms_view.py`, `engine/history_vault.py`, `ui/history_view.py`, and `ui/insights_view.py`.

### 9. Meeting notes and deliberation · existing

Local meeting capture, notes, and deliberation views are present. Their stored data is separate from the default never store dictation path. Code in `engine/meeting_notetaker.py`, `engine/meeting_deliberation.py`, and `ui/notetaker_view.py`.

## Product quality

### 19. Whole app usability and visual quality · planned · needs a decision

Review setup, dashboard, Studio, scratchpad, meetings, settings, and recovery as one user journey. Use one original visual system and keep navigation available when a view fails.

**Done when:** a new user can set a microphone and key, make a first dictation, recover a failed paste, find language and privacy settings, and return from every view, with readable light and dark layouts, keyboard access, and honest state labels. A control inventory covers each visible action, scrolling never changes an unintended setting, and display scaling keeps primary actions reachable.

- [ ] Design it (spec): `/architect whole app usability and visual quality`
