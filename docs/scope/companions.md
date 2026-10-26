# Companions

The companion should make dictation feel welcoming without interrupting the work underneath it. It remains an original native part of FlowPilot, not a copy of another app or character franchise.

## Existing foundation

### 10. Native companions and creator · existing

The HUD, tray, Studio, pixel creator, and opt in preference proposals are implemented. The selected character and its motion can be changed locally. App visibility rules now feed the native visibility controller in the working tree. Code in `ui/floating_hud.py`, `ui/companion_visibility_controller.py`, `ui/companion_studio.py`, `ui/pixel_creator.py`, `engine/companion_store.py`, and `engine/preference_learning.py`.

## Product quality

### 20. Context aware companion visibility · in progress

Keep the companion out of fullscreen viewing and presentations. Let users choose a quiet edge presence in selected editors and terminals, or keep the pet visible. Dictation and tray feedback continue while it is hidden.

**Done when:** entering and leaving fullscreen changes only presentation, manual hide persists, approved app rules apply, hidden animation stops, and no transition steals focus or changes paste status.

- [x] Design it (spec): `/architect context aware companion visibility`
- [x] Build the native policy, migration, controller, tray, dashboard, Studio and app rule controls.
- [x] Measure the automatable portion of the interactive gate on a live desktop: borderless fullscreen hide 0.203 s and 0.516 s, restore 0.610 s and 0.625 s, a maximized plain window holds the companion, and a full context sample stays under half a millisecond per call. Details in [the gate results note](../testing/COMPANION_VISIBILITY_INTERACTIVE_GATE_RESULTS.md). The probe needs a quiet desktop and reports unmeasurable rather than a pass when the operator keeps working.
- [x] Record the historical RC3 packaged live checks for Edge F11, a real PowerPoint slideshow, F9 text delivery while Hidden, and primary or secondary display frame fit. Evidence: [media validation note](../testing/MEDIA_AUDIO_PRESENCE_VALIDATION_2026-10-23.md). This does not verify every tray state or every target app or the later RC8 bytes.
- [ ] Complete the remaining live rows: Chrome F11 specifically, restart persistence, Studio app rule edits, reduced motion after hide/restore, tray states during hidden dictation, and fullscreen video on one monitor while editing on another. Record outcomes on the exact candidate rather than inferring them from unit tests.
- [ ] Decide release promotion after measured window transitions and pilot review.

Active implementation contract: [spec 0001](../specs/0001-context-aware-companion-visibility.md). Automated checks do not replace the interactive desktop gate, and the published RC8 archive remains unchanged until a new candidate is built.

### 27. Media audio aware hiding · in-progress

While any audible playback is active (video, music, podcast), a smart-mode companion hides itself and returns after 1.5 s of quiet, unless dictation is in flight, a manual mode is set, a per app rule applies, the foreground app is a quiet editor, or the temporarily shown state is active. The signal is the Windows render session meter (`IAudioMeterInformation` via pycaw), the same surface already used by the audio ducker; a muted or paused stream does not count as audible and window title, pixels, and clipboard stay untouched. Only continuous audibility of about one second hides the companion, so a short system sound never does the hiding. Code in `engine/media_presence.py`, `engine/companion_visibility.py`, `ui/companion_visibility_controller.py`, and `desktop_app.py`; coverage in `tests/test_companion_visibility.py`. This generalizes, and does not reopen, feature 24: it still cannot tell a windowed video from background music, it only treats audible playback as a viewing signal.

The audio session query runs in a background sampler so a slow COM call cannot stall the Qt event loop. A fresh sound after the quiet grace must pass the one second sustain gate again.

**Done when:** audible media hides the companion in smart mode, silence restores it, dictation states win over the hide, manual modes and app rules are untouched by the hide, and the probe fails soft without breaking the visibility tick.

- [x] Record the historical RC3 audible, muted, unmuted, and paused local video behavior in Edge with measured hide and restore times.
- [ ] Extend the live check to the intended browser playback workflow, music, notification sounds, quiet gaps, and interactions with manual modes and app rules. Do not label audio presence as video recognition.

Source and package evidence: [media audio validation note](../testing/MEDIA_AUDIO_PRESENCE_VALIDATION_2026-10-23.md).

### 21. Original character quality and rights · planned · needs a decision

Make a small set of expressive original characters and improve the creator so people can make and share their own without importing unsafe or unlicensed assets.

**Done when:** characters remain readable at desktop size in every dictation state, reduced motion works, import limits and credits are clear, and a rights review finds no copied franchise art or competitor bundle in the package.

- [ ] Design it (spec): `/architect original companion character quality`

## Later

### 23. Optional editor presence · planned · needs a decision

Explore an opt in status item inside a supported editor after desktop visibility rules are proven. Keep workspace and source content out of the integration by default.

**Done when:** an opted in editor can show truthful dictation status and open companion controls without a desktop overlay, editor focus loss, or non local traffic.

- [ ] Design it (spec): `/architect optional editor presence`

### 24. Windowed media and screen share behavior · closed · manual app rules

Research question: can a local signal distinguish foreground windowed video from background music without reading screen pixels or private content?

Answer from [the windowed video detection note](../research/WINDOWED_VIDEO_COMPANION_DETECTION.md): no provable local signal identifies a video in the foreground browser tab without reading content the companion must not touch. Feature 27 now hides the companion on sustained audible playback, including an ordinary sized video, but also including music. It leaves a muted video visible. Fullscreen and presentation signals remain independent. Explicit per app rules in Companion Studio provide a more precise choice for a whole app. True video recognition stays out of scope unless a future local, opt in signal passes the false hide and missed hide tests listed in the note.

**Done when:** a tested signal avoids false hides without reading screen pixels or private content, or the feature stays a manual app rule. Screen capture exclusion is evaluated separately and never described as a guarantee.

- [ ] Design it (spec): `/architect windowed media and screen share behavior`
