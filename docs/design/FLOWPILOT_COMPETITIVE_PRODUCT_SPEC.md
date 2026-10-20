# FlowPilot Windows product-parity and identity plan

Status: working specification, 2026-10-19. Scope: current local worktree, not the published v3.0.2 download. This is a comparison of user outcomes, not permission to copy Wispr Flow's artwork, wording, brand, or proprietary implementation.

## Product decision

FlowPilot should be the Windows dictation tool a developer can trust without an account or network connection: speak, see accurate text in the intended field, and recover it if an app refuses the paste. Companion creation is a distinct, optional reason to enjoy using the tool; it must never obscure the dictation task or editor focus.

"All Wispr features" cannot mean literal platform or cloud parity while FlowPilot's local-processing boundary remains binding. Mobile keyboards, cloud sync, team administration, remote model training, and calendar services are separate product lines. Match the **desktop outcomes** that users notice, or clearly mark them unavailable. No feature is called equivalent until an end-to-end test establishes it.

## Evidence and current-source inventory

Wispr's October 2026 documentation describes a desktop Hub with history, Dictionary, Snippets and Meetings; a floating Flow Bar; writing styles and contextual formatting; multilingual dictation; paste/copy recovery; Scratchpad; Command Mode; and Notetaker. Its features vary by plan and platform. Sources: [Hub](https://docs.wisprflow.ai/articles/5096240724-navigating-the-wispr-flow-app-desktop-ios-and-android), [languages](https://docs.wisprflow.ai/articles/3191899797-use-flow-with-multiple-languages), [context](https://docs.wisprflow.ai/articles/4678293671-context-awareness), [recovery](https://docs.wisprflow.ai/articles/7971211038-fix-text-not-pasting-after-dictation), [Scratchpad](https://docs.wisprflow.ai/articles/9618237082-using-the-scratchpad-to-save-and-edit-notes), [Command Mode](https://docs.wisprflow.ai/articles/4816967992-how-to-use-command-mode). These describe public behavior, not verified internal architecture.

The comparison cannot stop at Wispr. [Superwhisper for Windows](https://superwhisper.com/windows) advertises on-device dictation, app-aware formatting, languages and file transcription; therefore "offline" alone is not a unique claim. [Aqua Voice for Windows](https://aquavoice.com/windows) emphasizes technical vocabulary, style adaptation and speech accuracy while openly saying its audio is processed in the cloud. Its [Aqua Pet](https://aquavoice.com/pet) already offers a desktop character, cosmetic customization and usage-based unlocks; therefore "has a pet" alone is not a unique claim either. These are vendor-described capabilities, not independently benchmarked results. FlowPilot's testable differentiation is **private local execution + dependable Windows insertion + original, user-authored companion identity**.

| User outcome | FlowPilot source today | Gap before claiming parity |
| --- | --- | --- |
| Dictate anywhere with clear recording/processing feedback | Hotkeys, pre-roll, local STT, native HUD and recovery states exist in `engine/orchestrator.py`, `engine/text_injector.py`, `ui/floating_hud.py`. | Real cross-app first-paste, focus, no-duplicate and p95 visible-text trials; release model provisioning. |
| Pick languages and dictate naturally | Registry, settings/tray selector and local translation path exist. | Real native-speaker acoustic corpus, per-language error/latency, dialect/script handling, and honest support labels. |
| Personal words and reusable phrases | Dictionary and snippets exist in `engine/personalization.py` and Settings. | Make them first-class, searchable Hub destinations; test correction semantics and safe import. Do not imply automatic learning from edits without an explicit, privacy-reviewed implementation. |
| Format for the app and edit selected text | Deterministic profiles, app categories and selected-text transforms exist. | Browser-site-aware profiles, focused-field context with a strict timeout and secure-field exclusion, and raw-versus-polished review. Current process-category recognition is not field-level Context Awareness. |
| Find and reuse past work | Opt-in history, local Scratchpad, Insights and Notetaker views exist. | First-session explanation of separate retention scopes, reliable empty states, actual note editing/persistence tests, and real meeting consent/capture tests. |
| Voice command/edit workflow | Selected-text transforms exist; an optional localhost LLM can be configured. | No general spoken Command Mode parity. Define a small safe local command grammar first; require preview/confirmation for destructive edits or external actions. |
| Make the interface personally desirable | Companion Studio, pixel creator, emoji/PNG import, share packs, and several characters exist. | Curate original character quality and a 60-second adopt/customize path; measure whether users actually choose and retain it. Never use Pokemon names, silhouettes or copied sprites. |
| Trust and distribution | Local-first source, privacy documents, build/test tooling exist. | Prove fresh-machine offline dictation, publish an exact-source release with model assets or a disclosed offline model pack, consistent versioning, and scoped claims. |

## Interface direction: familiar workflow, original appearance

- Keep two surfaces: a tiny non-activating status companion/HUD during work, and a deliberately opened, focusable Hub for setup, history and creation. Do not make the passive HUD an always-open dashboard.
- The Hub's first screen should answer, in this order: **Can I dictate now?** **Which shortcut and language?** **What happened to my last dictation?** **Where are my words/snippets?** Companion access stays visible but secondary to those answers.
- Navigation should use plain, stable labels: Home, History, Dictionary, Snippets, Scratchpad, Meetings, Companion Studio, Settings. Group less frequent Insights and Transforms under a secondary section. Avoid a wall of nine companion buttons on the main task surface.
- Use FlowPilot's own cobalt/cyan, warm neutral surfaces, typography and original courier/Signal companion work; do not reproduce Wispr's exact bar geometry, iconography, microcopy, or illustrations. Offer restrained dark and light themes, high contrast, keyboard traversal, accessible names, and reduced motion.
- Show meaningful, truthful states: ready, listening, processing, inserted, sent-unverified, recovery available, microphone unavailable, model unavailable. An unverified paste is never a celebration. Separate user-requested interactive windows from the focus-preserving passive HUD.
- Never show an unconditional "ready" state before the selected microphone and model are usable. A first-run setup should test both locally and allow a plain-text trial with a visible recovery action.

## Delivery sequence and acceptance gates

### P0 — Release and trust foundation (in progress elsewhere)

Fix the known injector clipboard-failure crash, source/version mismatch and missing clean-machine model proof before any new public release. Run the full runner and physical Windows trials against the exact packaged build. Keep any dirty, concurrent work intact; do not publish a candidate by merely renaming the ZIP.

### P1 — Core experience and discoverability

1. Repair home-card navigation and add a regression test for every visible shortcut. This small fix is already in the current worktree.
2. Add a first-run local-readiness flow: microphone selection/test, model availability, language selection, a one-sentence test dictation, and recovery practice. No account and no silent download. Persist only explicit choices. A failed prerequisite must name the fix and keep the app usable for Settings/Help.
3. Move Dictionary and Snippets out of the crowded Settings dialog into discoverable Hub pages while reusing `PersonalizationEngine`, tombstones and current storage. Search, add, edit, delete, import/export and keyboard access need focused tests. No background monitoring of edits.
4. Show last-dictation status and copy/paste recovery on Home and tray. Preserve status distinctions and guard against duplicate re-paste.

Acceptance: a new user can install offline, complete setup, dictate into Notepad and VS Code, find/correct a word, add a snippet and recover a failed paste without reading repository documentation. Every visible navigation action opens the named destination. No app surface steals focus during ordinary dictation.

### P2 — Accuracy and app-aware writing

1. Benchmark actual spoken English plus a deliberately small set of pilot languages; publish per-language WER/CER, identifier/fact error and stop-to-visible-text latency. Expand support labels only after evidence.
2. Add opt-in, bounded focused-field context only after a separate privacy/security design. Exclude password, secure, finance and URL fields; impose a 500 ms worker timeout; do not log or persist field text. Process title/category alone is not equivalent.
3. Make writing profiles easy to understand with before/after examples and a per-dictation raw fallback. Preserve numbers, negation, dates and identifiers in all profiles. Keep optional localhost LLM transformation clearly separate from guaranteed local deterministic dictation.

Acceptance: tests include difficult real audio, target-app context, privacy exclusions, and FactGuard adversarial fixtures. Field-context failure does not block dictation or send network traffic.

### P3 — Delight and advanced workflows

Polish one original companion family and a guided adopt/customize/share flow before multiplying presets. Test preview/Apply/Cancel, performance, no focus theft, and reduced motion. Improve Scratchpad/meeting workflows with consent and retention clarity. Consider a narrow local Command Mode only after core dictation reliability is measured; do not add broad agent actions as a substitute for accurate words.

Acceptance: companion creation takes about a minute, can be skipped entirely, uses owned/licensed assets, and does not regress CPU, memory, focus or dictation latency. Meeting and command features have explicit safe failure paths.

## Test ownership and evidence rules

- Automated: navigation, storage migrations, status propagation, secure-field exclusion, timeout/failure cleanup, and no-egress tests in the full suite.
- Interactive Windows: Notepad, VS Code/Electron, Chromium field, terminal and at least one slow app; measure first-pass insertion separately from manual recovery. Repeat across fresh profiles and screen/DPI variants.
- Audio: identical WAV input routed through VB-Cable for each compared tool, plus consented human speech. Retain full fixture hashes, language, microphone route, settings, source revision and latency start/end definitions. Never call local processing time stop-to-visible-text.
- Visual: screenshots at 100%, 125% and 150% DPI in dark/light/high-contrast themes; keyboard-only and screen-reader checks; passive HUD focus invariant.
- Pilot: 5–10 developers. Record task completion and failures without collecting transcript content. Ask separately whether they would keep using dictation and whether the companion increases desire to install/retain it.

Completion means the user journeys and evidence gates pass on a traceable release artifact. A suite count alone is not a product-parity claim.
