# FlowPilot Companion Studio and Local Learning

> **Dated design proposal (October 17, 2026):** This records the original problem, alternatives, and acceptance criteria. Some sections describe behavior before the Studio implementation and the implementation checklist below has not been maintained as a release-status report. Inspect current source and [live CI](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml) for the implemented state. The requested Gemini review did not return a review.

Date: 2026-10-17  
Status: Proposed design; implementation has not started.  
Baseline inspected: `262a705`.  
Audience: FlowPilot maintainer, Gemini reviewer, implementing coding agent.

## 1. Product decision

Build **Companion Studio inside the existing FlowPilot desktop application**. It gives the user a reliable place to choose a character, make a small personal creation, control animations, and inspect what FlowPilot remembers. Keep one application, one tray icon, one microphone owner, and one Qt event loop.

The product promise: **Choose a companion that stays yours, teaches you its controls, and remembers only what you allow.**

This is an existing-user improvement, not a new standalone agent platform. The user reports that repeated clicks unexpectedly change the kitty. Source inspection confirms `FloatingHUD.mouseDoubleClickEvent()` calls `toggle_visual_style()`, cycling mascot, kitty, edge line, and waves. Single-click release also toggles dictation. Appearance selection is therefore coupled to an ambiguous recording gesture.

The narrow first release is a stable character plus a clear customization window. Local learning follows once customization and dictation are reliable. A large character marketplace, unrestricted automation agent, or model-training pipeline would delay the actual benefit.

## 2. Scope and release sequence

| Release | User outcome | Included | Deferred |
| --- | --- | --- | --- |
| A: Stable companion | My kitty stays selected; I can always find it | Explicit selection, appearance lock, restore/show action, Studio shell, existing four styles, palettes, placement, reduced motion | Imports and learning |
| B: Personal creations | I can make and use my own little character | Emoji, PNG, PNG sprite sheet, six motion presets, six state slots, local library, data-only export/import | GIF/video imports, generative model, marketplace |
| C: Local memory | FlowPilot remembers my approved preferences | Editable memory cards, explicit vocabulary teaching, app profiles, optional preference suggestions, undo/forget/pause | Hidden monitoring, background transcript collection, model fine-tuning |
| D: Evidence-led expansion | Repeated useful actions become reusable recipes | A small whitelist of local preference recipes after pilot evidence | Arbitrary code, shell tools, web agents, autonomous installs |

Use existing kitty/robot/line/wave assets. Ship no more than six built-in motion presets: breathe, blink overlay, gentle bob, tiny tilt, audio pulse, and one-shot celebration. The emoji and import slots provide variety without maintaining dozens of characters.

## 3. Interaction contract

### Companion controls

- Single click preserves the current start/stop dictation behavior.
- Double click never changes appearance. Classify the sequence so it produces at most one dictation toggle; suppress the second release rather than adding a full double-click waiting delay to every single click. Verify real Qt event sequences and Windows double-click settings.
- Drag moves the companion; releasing after a drag never records or changes appearance. Use the platform drag threshold, not a hard-coded four-pixel test.
- Right click offers Show Studio, Pause Motion, Move To, Hide, and existing dictation/recovery actions. Style cycling is replaced by explicit selection.
- Appearance is locked by default: ordinary pointer gestures and learned preferences cannot select another asset. Studio Apply can intentionally change it.
- Tray actions always include Show Companion, Open Companion Studio, and Restore Bottom-Right. Show also raises without activating; Restore uses the current monitor work area and 24 logical-pixel padding.
- Persist hidden state explicitly and label it in Studio. Remember the selected asset separately from visibility and placement.
- Recover invalid/off-screen placement after monitor removal or DPI changes. Negative desktop coordinates are valid on secondary monitors; do not treat all negative coordinates as corrupt.

### Studio layout

```text
Companion Studio                         [Show companion] [Close]
Library | Create | Behavior | Memory

Library:                   Preview:
[Kitty] [Robot]             [large live character]
[Line]  [Waves]             Idle / Listening / Processing / Success
[My creations]             Current selection and accessible name

Appearance / Size / Palette / Motion / Sound / Placement
                                      [Cancel] [Apply]
```

Preview changes remain drafts until Apply. Cancel and window close discard draft edits. Apply atomically persists a validated snapshot and updates the live companion through a Qt signal. Preview states never start the real microphone, inject text, play system sounds, or generate learning events.

Studio is opened explicitly from the tray or menu. It never appears automatically during dictation. If recording or processing is active, defer opening until completion and show a non-activating status indication. Closing Studio never restores focus by synthetic Alt keys or aggressive foreground manipulation. The next dictation captures its target anew.

### Focus contract that must be reconciled in the directive

The existing directive literally prohibits focus on every QWidget. A text-entry settings window cannot support keyboard editing under that rule. This design proposes a narrow clarification: **passive HUD and automatic UI never activate; an explicitly opened Studio may receive keyboard focus while dictation capture/injection is gated.** Existing settings already use ordinary dialog interaction. Record this exception in the implementation change; do not silently apply HUD no-focus flags to all Studio controls or silently relax HUD protection.

If the broad prohibition must remain literal, restrict the interface to pointer-only preset selection and defer emoji typing, naming, and memory editing. That is a product tradeoff, not a Qt workaround.

Keyboard navigation, accessible control names, visible focus rings, sufficient contrast, high-DPI layout, and reduced-motion behavior are acceptance requirements. Errors use text and icons as well as color.

## 4. Creation flows

### Emoji companion

1. Create -> Emoji; type or paste a single Unicode grapheme cluster, including supported joined emoji and skin-tone sequences.
2. Preview the actual local font rendering. Explain missing-glyph fallback instead of substituting a different character silently.
3. Choose one motion preset, size, and optional state accent; name and save.
4. Apply to the live companion. Original Unicode remains stored; rendered output may differ by OS/font.

No network emoji catalogue is required. Qt renders the chosen glyph into cached local raster frames. The platform emoji picker is optional when Studio owns focus.

### Image companion

1. Create -> Image; choose a local transparent PNG.
2. Preview crop, transparent bounds, and scale. Do not promise AI background removal in this release.
3. Choose a motion preset and state accent; save to the local library.
4. Removing the original source image after import must not break the saved creation.

### Animated sprite companion

1. Create -> Sprite Sheet; import a PNG grid and specify frame width, height, and count.
2. Select frames for idle, listening, processing, success, error, and cancelled states.
3. Preview loop speed and transitions. Missing state animations fall back to idle with a small status accent.
4. Save and apply. Success/error animations run once; they do not replay when the same event is delivered twice.

Initial limits are **proposed engineering limits**, to be validated on the target machine: 2 MiB source file, maximum 1024 x 1024 source image, 24 source frames total per pack, normalized 96 x 96 logical-pixel cells, and maximum 2 MiB decoded active sprite cache. Enforce the decoded-byte budget at the actual device pixel ratio. Reject or explicitly offer rescaling when a pack exceeds it. Do not trust compressed size alone.

Only PNG and a versioned JSON manifest are accepted initially. Reject absolute paths, traversal, symlinks escaping the selected package, remote references, scripts, HTML, executable files, and unsupported manifest versions. Validate headers and dimensions before full decoding; validate actual decoded data as well. Stage imports, verify hashes and schema, then publish atomically. Failed imports leave the current companion intact.

Export a selected creation only: manifest, normalized images, attribution/license field, and optional thumbnail. Exclude memory, app profiles, audio, clipboard content, transcripts, and absolute source paths. Built-in third-party assets retain their license/attribution requirements.

## 5. Hermes-inspired learning, adapted to FlowPilot

Hermes documents persistent reusable skills and learning procedures from experience. The useful pattern here is a small visible loop: **user action -> evidence -> proposed preference -> approval -> reusable rule -> feedback -> undo or refinement**. This is a design adaptation, not a claim that FlowPilot already runs Hermes or trains its own model.

Source: [Hermes Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills). Accessed 2026-10-17. Do not embed Hermes, copy its runtime, or connect its cloud providers for this feature.

### Three explicit memory categories

| Category | Example | Collection and activation |
| --- | --- | --- |
| Preferences | Kitty, muted celebrations, preferred size | Explicit Apply persists immediately; no separate learning consent needed for ordinary settings |
| Personal vocabulary | A user-entered alias for a project term | User opens Teach a Word and reviews the exact alias/term; protected-token checks run before activation |
| Suggested app preferences | The user repeatedly chooses reduced motion for a specific editor profile | Optional learning enabled by user; count only deliberate FlowPilot settings actions, then propose a rule |

Do not infer corrections by watching keystrokes, reading the clipboard, scraping editor documents, capturing screens, or retaining dictation history. A user may deliberately enter an alias/term pair in Studio. Do not prefill full transcripts into durable learning storage.

Vocabulary aliases that alter numbers, dates, negation, or protected code identifiers must be rejected or confined to a separately specified explicit formatting command. Approval does not waive FactGuard invariants. Prefer approved vocabulary as ASR prompt bias where appropriate; test deterministic rewriting separately.

Learning defaults off. Ordinary saved preferences work when learning is off. Enabling learning permits bounded, local counts of Studio choices and approved app identity, not general activity monitoring. Use executable basename/category already available to FlowPilot; exclude window titles, file names, URLs, screenshots, and document content.

### Initial suggestion policy

- Consider a suggestion after the same deliberate preference is chosen on three distinct days for an app scope, with at least 80% agreement among eligible choices for that setting in the preceding 14 days. These are initial heuristics, not model-confidence scores.
- Count at most one observation per setting/app/day. Repeated clicks, preview actions, tests, and automatic state changes do not count.
- Show suggestions only in Studio Memory; no unsolicited popups or interruptions. At most one new visible suggestion per day.
- Each card explains the setting, app scope, evidence count, proposed effect, and controls: Accept, Dismiss, Never Suggest This.
- Explicit current-session settings outrank app rules; app rules outrank global defaults. A manual choice pins the setting until the user unpins it. Rejected or forgotten rules do not regenerate from retained counts.
- No preference rule can change hotkeys, select a cloud provider, disable FactGuard, change injected text, or choose an appearance while appearance lock is on.

Example: the user deliberately selects reduced motion for the editor on three days. Studio offers “Use reduced motion for this editor?” Acceptance creates one readable rule. Undo removes the rule immediately and prevents immediate regeneration. The character never changes on its own.

### Memory controls and retention

Every rule exposes origin, scope, created/updated date, evidence summary, enabled state, and last application. Supply Edit, Disable, Forget, Undo Last Change, Pause Learning, and Forget Learned Data. Explain that Pause stops new observations but leaves accepted rules active; disabling accepted rules is a separate action.

Keep aggregated evidence for at most 30 days, at most 200 active rules and 100 pending suggestions. Approved vocabulary/preferences remain until deleted. Expired observations are pruned at load/save. Clear-learning removes evidence, suggestions, learned rules, and their undo records; ordinary visual settings remain unless Reset All is selected. Deletion covers backups/journals used by these stores; do not claim forensic secure erasure on SSDs or OS backups.

Future recipes are data-only combinations of existing preferences, such as “editor quiet mode.” No arbitrary Python, shell execution, filesystem browsing, downloads, self-modifying code, online calls, or unattended actions. Local LLM suggestions are deferred until deterministic learning proves useful and hardware budgets are measured.

## 6. Technical architecture and reuse

Reuse the existing renderer, palettes, tray, config loader, personalization dictionary/snippets, app-profile resolver, and orchestrator notifications. Add small interfaces around them instead of rewriting the dictation engine.

```text
Orchestrator state + RMS + session token
                    |
          CompanionStateAdapter
                    |
        FloatingHUD / QPainter <--- applied config snapshot
                                      ^
Studio draft -> validate -> CompanionStore -> change signal
                    |
Explicit settings actions -> bounded evidence -> suggestion engine
                                               |
                                   Memory review -> approved rules
```

Proposed file ownership (names are planned, not existing APIs):

| File | Responsibility |
| --- | --- |
| `ui/companion_studio.py` | Single-instance Studio dialog, draft editor, tabs, Apply/Cancel |
| `ui/companion_preview.py` | Preview sharing rendering logic without live engine side effects |
| `ui/floating_hud.py` | Stable pointer behavior and passive live rendering |
| `ui/tray_manager.py` | Explicit Studio/show/restore commands |
| `engine/companion_assets.py` | Manifest validation, bounded imports, local asset lookup |
| `engine/companion_state.py` | Pure state mapping, event priority, stale-session rejection |
| `engine/companion_store.py` | Versioned settings/assets metadata, atomic persistence, migrations |
| `engine/preference_learning.py` | Bounded evidence aggregation, proposals, rule precedence |
| `engine/personalization.py` | Existing vocabulary integration; scoped fixes for durable deletion |
| `desktop_app.py` | Own Studio instance and connect signals; focus/lifecycle policy |

Keep QPixmap creation/use and QWidget mutation on the GUI thread. Image inspection and normalization may use a bounded worker with QImage/data results delivered via signals. Never decode or read files inside paintEvent or PortAudio callbacks. Do not start an extra microphone, application process, server, or socket bridge for Studio.

Map existing states: IDLE -> idle; STARTING_RECORDING -> ready indicator; RECORDING -> listening; STOPPING_RECORDING/TRANSCRIBING/VALIDATING/INSERTING_TEXT -> processing; confirmed success -> success; sent-unverified -> subdued sent state; ERROR -> error; CANCELLED -> cancelled. Do not celebrate confirmed insertion when the engine reports sent-unverified. Newer session tokens invalidate queued old animations. Error/cancel events outrank success; audio amplitude never overrides semantic state.

## 7. Storage, migration, and recovery

Use the existing user-local FlowPilot directory with injected alternate paths in tests. Keep versioned JSON for this modest scope, with one owning writer; do not introduce a database unless measured needs justify it.

- `companion.json`: schema version, selected asset id, appearance lock, visibility, size, motion, sound, logical position and monitor hint.
- `companions/<id>/manifest.json` and normalized PNG: data-only creation. IDs are application-generated, not user-supplied filesystem paths.
- `learning.json`: enabled flag, bounded aggregate evidence, proposals, approved preference rules, suppression records.
- Existing `personalization.json`: explicit approved vocabulary and snippets; avoid duplicating terms into a second source of truth.

Write a validated temporary file in the same directory and atomically replace the destination. Use a generation counter to reject stale Studio/config snapshots; merge only owned keys. A local lock cannot protect against another process writing the same store: either enforce one writer across desktop/integration bridge or disable those writes until a shared store contract exists. Never overwrite current history/settings from a stale full-config copy.

On first migration preserve `hud_style`, `hud_x`, `hud_y`, `cat_palette`, and `cat_sound`. Existing selection wins over defaults. Map the four built-ins to stable asset IDs. Invalid manifests fall back to the last known-good built-in with a Studio explanation. Missing custom assets never crash the dictation pipeline. Remove selected assets only after switching to a valid fallback; undo metadata changes without restoring forgotten learning data.

Current `PersonalizationEngine.load()` reintroduces defaults absent from disk. Add a one-time initialization/version marker or deletion tombstones before promising persistent Forget/Delete. A deleted term must stay deleted after restart and update.

## 8. Performance and privacy gates

The directive's paint <0.2 ms, incremental companion memory <5 MB, smooth 60 Hz presentation, and speech-end-to-verified-insertion p95 <1.5 s are **targets requiring evidence**, not current certifications.

Measure companion memory against the same process with the companion disabled, after warm-up, using the same model, pack, DPI, and workload. Track peak and steady delta, not only Python allocations. Limit active decoded sprites to 2 MiB and lazily load thumbnails; measure remaining Qt/platform overhead. If the 5 MB target cannot be met, reduce pack complexity or explicitly revise the budget before release.

The full editing window allocates more controls and preview resources. Report Studio memory separately. Applying the original 5 MB ceiling to an entire editor is an unresolved scope issue: propose retaining it for the persistent companion and setting a measured editor budget; do not silently reinterpret the directive. Close Studio previews and release caches when hidden.

Render to the existing Qt event loop, scheduling smooth presentation only when motion changes. Static/reduced-motion states do not need constant repainting. Pause hidden previews; animate only one selected library preview. No background learning job runs during recording/transcription; aggregate tiny events and process them after the session. Measure with learning enabled/disabled and Studio open/closed.

All application inference, imports, rendering, memory, and proposals remain local. No fetched URLs in asset manifests. No audio/transcript/clipboard/screen data leaves the workstation. Gemini's design review is a separate user-requested development activity containing only this design, not runtime user data or an application dependency.

## 9. Baseline prerequisites and executable milestones

The reviewed baseline has unresolved CI and injection issues. Keep their remediation visible; a new UI must not be described as fixing the engine. The observed `262a705` CI result was 21 passes, 2 skips, 7 failures: [run 38966898160](https://github.com/abishekvr0910/flowpilot/actions/runs/38966898160). This is historical evidence, to recheck before implementation.

| Milestone | Work and dependencies | Exit evidence |
| --- | --- | --- |
| M0: Honest baseline | Remove broad Notepad termination from tests; repair clipboard ownership checks and guaranteed key/thread cleanup; resample decoded WAV correctly; distinguish real VAD from RMS; align packaged assets/tests and hardware CI | Reproductions pass; complete runner separates pass/fail/skip; no destructive global cleanup; known failures resolved or explicitly block release |
| M1: Stable selection | Pointer contract, explicit style selection, show/restore, versioned companion store and migration | Repeated/double clicks never change asset; drag never records; selection persists; multi-monitor recovery passes |
| M2: Studio | Native dialog, one instance, shared preview, Apply/Cancel, keyboard interaction and explicit focus policy | No live side effects from previews; Cancel preserves settings; active dictation cannot be retargeted to Studio |
| M3: Creation library | Emoji/PNG/sprite imports, bounded cache, preset animation, package export | Valid packs survive restart; invalid/oversized/traversal packs rejected; no external resource access; resource budgets measured |
| M4: Local memory | Explicit teaching, opt-in evidence, suggestion cards, precedence, retention, undo/forget | Deterministic replay tests; disabled learning writes no evidence; forgetting survives restart and defaults migration |
| M5: Integration release | Packaging, entry points, hardware tests, soak/performance measurements, brief usability pilot | CI green for applicable checks, hardware evidence for skipped checks, same-build artifact tested, all requirements traceable |

Implementation order: M0 and M1 first, then M2 -> M3 -> M4 -> M5. Prototype Studio while baseline repair proceeds only if isolated from shipping changes. No deadline promise: M0 has unknown remediation effort. Re-estimate after baseline evidence and a small Studio prototype.

## 10. Acceptance matrix

| ID | Scenario | Observable result |
| --- | --- | --- |
| UX-01 | Twenty single/double-click/drag sequences | Zero appearance changes; at most one dictation toggle per classified click sequence; no drag activation |
| UX-02 | Hide, restart, restore; disconnect secondary monitor | Clear hidden state and reliable visible placement with no focus theft |
| UX-03 | Preview each state; Cancel; Apply | Preview never activates live capture/injection; only Apply persists |
| UX-04 | Keyboard-only emoji creation at 100/150/200% DPI | All controls usable, joined emoji preserved, labels readable |
| AS-01 | Missing/malformed/oversized imported pack | Clear error; live companion remains valid; no partial publish |
| AS-02 | Import paths/remote URI/script attempts | Reject without network or code execution |
| ST-01 | Late success arrives after cancellation/new session | No stale celebration or state change |
| LR-01 | Learning disabled for ten sessions/settings changes | No new learning evidence; ordinary explicit settings still persist |
| LR-02 | Three-day preference evidence with conflicts | Exact threshold behavior; explanation is accurate; manual override wins |
| LR-03 | Reject, forget, restart, upgrade | No rule resurrection from defaults, aggregates, or undo history |
| LR-04 | Protected-token vocabulary examples | Negation, numbers, dates, identifiers retain required invariants |
| PR-01 | Run new features with external networking denied | Features work; attempted external operations fail the test |
| PF-01 | Worst allowed pack, mixed DPI, active dictation | Paint/memory/latency measurements meet agreed budgets; no audio underruns attributable to Studio |
| LC-01 | Open/close Studio 50 times; exit during import | No extra mic/process owner; workers terminate; bounded memory growth |

Use injected temporary stores, fake clocks, synthetic state streams, and test-owned windows/processes. GUI tests must track their own HWND/PID and restore test-controlled clipboard state without overwriting a newer user copy. Hardware tests run on an explicit hardware runner and report skips honestly elsewhere. Never count a skip as evidence of the skipped behavior.

Usability pilot: five target users should find Show Companion and choose a fixed kitty within one minute without explaining double-click cycling. Record accidental recording/style changes and successful import completion. For learning, measure useful accepted suggestions and immediate reversals locally with opt-in test participants; set release thresholds after observing a baseline rather than inventing retention claims.

## 11. Decision record and review questions

Recommended now: in-app Studio; four existing styles plus personal creations; six small animation presets; appearance locked; preference-based learning; explicit vocabulary teaching; all-local runtime.

Before implementation, record the narrow explicit-Studio focus exception and the distinction between persistent-companion and editor memory budgets. These are the two directive interpretations that need explicit treatment in the implementation proposal.

Ask Gemini to challenge: event-sequence correctness, edit-window focus transitions, manifest memory limits, state precedence, deletion semantics, justified scope, real usefulness of learning, and whether the acceptance criteria can actually be measured. Gemini should label assumptions and avoid replacing unresolved failures with promises.

## 12. Progress and handoff

- [x] Inspect current customization and personalization code.
- [x] Identify double-click appearance cycling as the reported behavior.
- [x] Specify product scope, flows, state/data contracts, milestones, and tests.
- [ ] Obtain Gemini review and record accepted/rejected recommendations. Attempted 2026-10-17; installed Gemini CLI rejected authentication with `IneligibleTierError` / `UNSUPPORTED_CLIENT`. No review was returned. See `GEMINI_REVIEW_STATUS.md`.
- [ ] Implement the approved feature scope in separate reviewable changes.
- [ ] Validate packaged behavior and obtain release evidence.

This document is a proposed plan. It does not certify performance, implement the Studio, or claim a successful Gemini review before one is received.
