# Companion visuals: research and proposed direction

Date: 2026-10-18. Status: research and implementation brief; no runtime changes.

## Recommendation

Focus the next visual pass on two polished choices: a quiet signal indicator for focused work, and one original FlowPilot character for users who enjoy a companion. Keep the existing cat available subject to completing its source/notice review. Defer additional animal variants until the core styles have consistent motion and state feedback.

This research reviewed local rendering code and upstream documentation. It did not include a live visual review or measured render-performance comparison. The proposed artwork and timings below are design decisions to prototype, not observed benchmark results.

## What the current code explains

| Observation | Why it matters | Proposed change |
| --- | --- | --- |
| `ui/companion_preview.py` and `ui/floating_hud.py` independently draw the robot, edge line, and waveform. Their dimensions, state colors, and animation rules differ. | Studio can show a different result from the desktop. | Use one renderer and state mapping in both surfaces; supply simulated audio only as an input to the preview. |
| Preview waveform heights follow a sine wave regardless of listening state. Desktop bars mix microphone level with a sine wave. | Motion can continue without representing speech. | During listening, drive an envelope display from measured audio. Use a visibly different processing loop. Do not label an envelope display a frequency spectrum. |
| Reduced motion gates the preview's outer transforms and the HUD's custom-companion transforms; internal built-in animation keeps advancing. | The setting does not consistently suppress the motions users expect it to suppress. | Apply reduced motion to the common animation state, including blinking, paws, rotating eyes, waveform loops, and celebrations. Keep static state symbols. |
| Timing is largely based on incrementing `_tick`, with a 33 ms preview timer. | Different refresh schedules can change animation speed. | Calculate phase and transitions from elapsed time; use the timer to request repaint. |
| Preview applies smooth pixmap transformation globally. | Scaling or bobbing pixel sprites at fractional positions can soften the artwork. | Give pixel art a separate sampling policy and snap its final placement to the device-pixel grid. Validate fractional Windows display scaling. |

These findings support a shared motion/rendering pass before adding more art. They do not establish that every unattractive visual was copied.

## Art origin and reusable sources

**Existing cat.** The local sprite module identifies itself as SondeR cat, and the README uses the SondeR-Cat name. The inspected `THIRD_PARTY_LICENSES.md` does not list that project. Upstream currently publishes an Apache-2.0 license and a NOTICE naming Verisonder and explaining attribution/origin expectations. Trace the exact imported revision and assets, retain the applicable license and notices, identify modifications, and verify that packaged distributions include them. This review has not established byte-for-byte provenance or the license of the originally imported revision. See the [upstream license](https://raw.githubusercontent.com/Verisonder/SondeR-Cat/main/LICENSE) and [NOTICE](https://raw.githubusercontent.com/Verisonder/SondeR-Cat/main/NOTICE). Treat the notice as attribution information; its wording does not amend Apache-2.0.

**Optional animal art.** [Kenney Animal Pack Remastered](https://kenney.nl/assets/animal-pack-remastered) lists 240 files under CC0. It is a candidate for optional user-selectable animals, not a ready-made dictation animation system. Confirm the chosen files and included license before importing; the app-specific poses and transitions would still need design.

**Optional emoji art.** [Microsoft Fluent Emoji](https://github.com/microsoft/fluentui-emoji) provides an established visual collection under [MIT](https://github.com/microsoft/fluentui-emoji/blob/main/LICENSE). Preserve its copyright/license when bundling assets. Use a small selected set for customization; it does not give FlowPilot a unique mascot or supply the required dictation state animations automatically.

**Motion reference.** [Fluent 2 motion guidance](https://fluent2.microsoft.design/motion/) emphasizes purposeful, natural, consistent motion and a no-motion option. Adopt those principles while developing FlowPilot's own shapes and character design.

## Two directions to prototype

### 1. Signal: quiet default indicator

A small neutral capsule with a recognizable FlowPilot accent. A compact five-bar audio envelope expands when listening. Processing becomes three restrained moving dots. Idle is still. A docked edge version uses the same colors, timing, and state symbols rather than a separate visual language.

Use a dark/light adaptive outline so it remains visible over editors and browser pages. Keep the interaction area stable as the artwork animates. Avoid large glows and persistent bouncing.

### 2. Pilot: original optional companion

Create an original compact pixel courier robot: a readable silhouette, a small visor, short feet, and a limited palette. Develop new source art with its own proportions and poses; do not trace the cat or another product's mascot. The user's preference for the cat suggests testing a similarly crisp pixel treatment before spending more time on the current glossy vector head.

Author a small set of intentional poses: resting, attentive, listening, working, acknowledgement, and recovery. Start with 2-4 frames per pose and validate the total against the current importer/package limits. Audio should influence a small part of the character, such as a visor meter or hands, rather than stretching its entire head continuously.

## State and motion contract

The timing ranges below are starting points for review at the actual desktop size.

| State | Signal | Pilot | Motion rule |
| --- | --- | --- | --- |
| Idle | Small still marker | Resting pose; occasional blink | Sparse motion, no continuous bouncing |
| Listening | Audio-driven envelope | Attentive pose with small audio response | Start with 40-70 ms attack and 120-180 ms release smoothing |
| Processing | Restrained dots | Working pose | Distinct 800-1,200 ms loop; no false percentage |
| Confirmed insertion | Brief check | One acknowledgement | One 250-400 ms transition, then settle |
| Sent but unverified | Neutral pending/recovery marker | Neutral waiting pose | Do not imply the destination has confirmed insertion |
| Failed, text recoverable | Persistent recovery symbol | Concerned/resting pose | Expose Paste Last; avoid a looping alarm animation |
| Reduced motion | Static state symbol | Static state pose | No ornamental transforms or autonomous loops |

Use shape as well as color to distinguish states. Feed these states from the actual injection result; painting a success pose must not decide whether a paste succeeded.

## Native implementation plan after the test fixes

1. Resolve the cat provenance record and prepare small original Pilot pose studies at their final display size. Compare against Signal on both dark and light desktops.
2. Introduce a common `CompanionRenderer` and elapsed-time animation state consumed by both Studio and HUD. Normalize engine state aliases at one boundary. Preserve existing appearance IDs and saved choices.
3. Use cached QPixmaps for sprites and QPainter geometry for Signal. Include palette, device-pixel ratio, frame, and mirroring in cache keys; bound the cache. Keep rendering in the existing Qt process. Qt documents [QPixmap device-pixel ratios](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPixmap.html) and [QElapsedTimer](https://doc.qt.io/qtforpython-6.10/PySide6/QtCore/QElapsedTimer.html) for the underlying primitives.
4. Stop repainting hidden previews and static states; schedule the next blink instead of continuously drawing identical idle frames. Measure paint time, incremental memory, and idle/active CPU before publishing performance claims.
5. Review all states at 100%, 125%, 150%, and 200% Windows scaling. Compare Studio and HUD for the same state/time/audio input. Verify reduced motion, focus preservation, stable click/drag behavior, and migration of existing companions. Complete the repository regression gate for implementation changes.

Suggested scope: one shared renderer, one original character, and one coherent indicator family. Asset creation and visual review are separate deliverables from code tests. No new gallery, online asset downloads, or additional companion families are needed for this pass.
