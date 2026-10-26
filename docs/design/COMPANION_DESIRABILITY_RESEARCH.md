# FlowPilot companions: something people want, not just another setting

Research date: 2026-10-18. Status: proposed product direction, awaiting approval; no application implementation in this research pass.

This extends the [visual research brief](COMPANION_VISUAL_RESEARCH.md). It does not replace Gemini's shared renderer, Signal, or Pilot work. Repository observations refer to the local, uncommitted worktree inspected on this date, not a verified GitHub release.

## 1. Decision in plain English

Build a small, original desktop character that people enjoy owning, then let them make it theirs. Do not lead with a blank drawing canvas, an emoji picker, or a promise of unlimited AI-generated pets.

The proposed experience is **choose a companion → give it your finishing touches → let it quietly accompany real work → keep and share your creation**. Dictation must remain excellent without the character. The character must be appealing without a feature-list explanation.

The Kinder Joy analogy suggests two independent reasons to choose FlowPilot: useful private dictation and a delightful personal object. That is a product hypothesis, not evidence that toy buyers will become dictation customers. The first test should measure both attractions separately.

Recommendation: prototype three original character concepts, finish only the strongest one, and build a short guided personalization flow around it. Keep Signal and the existing licensed cat available. Do not start a marketplace, daily reward economy, or conversational AI companion.

## 2. What the evidence actually establishes

### Adults buying toys is a real category, not proof of our market

Circana reported that US toy sales for adults aged 18+ reached $1.8 billion in Q1 2025, up 12% year over year. Its separate European report uses a 12+ definition that includes teenagers; these audiences must not be conflated. This supports investigating adult enjoyment and collecting, but does not measure demand for Windows desktop companions or FlowPilot. [US source](https://www.circana.com/post/toy-industry-us-sales-grow-in-early-2025-circana-reports), [European definition](https://www.circana.com/post/playful-profits-fandom-and-nostalgia-fuel-growth-of-teens-and-adults-4-5bn-toy-market-in-europe).

Kinder Joy's official offering combines a consumable treat with a surprise toy. Separately, Kinder's history of **Kinder Surprise**, a different product, describes constructive play, discovery, and shared adult/child enjoyment. These are brand descriptions, not independent evidence that parents primarily buy Joy for themselves. The useful analogy is a satisfying main product plus an object worth keeping, not chocolate packaging or paid blind-box mechanics. [Kinder Joy](https://www.kinder.com/us/en/kinder-joy), [Kinder Surprise history](https://www.kinder.com/au/en/the-kinder-story/04).

### Digital companions have visible demand signals

These are English-language Steam review snapshots retrieved on the research date. They are not sales, revenue, unique active users, age profiles, or retention measurements.

| Product | Observed review signal | What it establishes |
| --- | --- | --- |
| [Bongo Cat](https://store.steampowered.com/app/3419430/Bongo_Cat/) | 30,461 English reviews; 96% positive | A simple reactive companion and cosmetic collection can attract substantial review activity. Free availability prevents interpreting this as willingness to pay. |
| [Rusty's Retirement](https://store.steampowered.com/app/2666510/Rustys_Retirement/) | 6,608 English reviews; 97% positive | A paid, peripheral desktop experience can find an appreciative audience. It is also a farming game, not a dictation tool. |
| [Spirit City: Lofi Sessions](https://store.steampowered.com/app/2113850/Spirit_City_Lofi_Sessions/) | 9,152 English reviews; 97% positive | A paid productivity-adjacent experience can combine personalization and creature collecting. The music, room, and tools contribute too. |

Selection bias matters: these are deliberately chosen successful comparables, not a representative sample of all companion apps. Their success cannot identify which individual feature caused adoption.

### Nine useful comparisons, including a counterexample

The last column is a proposed FlowPilot interpretation, not a claim about a competitor's internal design research.

| Reference | Observable mechanism | What FlowPilot should learn / avoid |
| --- | --- | --- |
| [Kinder Joy](https://www.kinder.com/us/en/kinder-joy) | Treat plus a small surprise object | Make the companion worthwhile beyond the utility. Avoid paid randomness and imitation branding. |
| [Bongo Cat](https://store.steampowered.com/app/3419430/Bongo_Cat/) | Immediate response to typing/clicking; collectible hats | A clear reaction and visible accessory are legible at a glance. Use existing dictation events, not a new global key-monitoring system. |
| [Rusty's Retirement](https://store.steampowered.com/app/2666510/Rustys_Retirement/) | Peripheral farm, helpers, configurable placement, focus mode | Support a quiet corner and low-attention enjoyment. Do not import an entire management game. |
| [Spirit City](https://store.steampowered.com/app/2113850/Spirit_City_Lofi_Sessions/) | Spirits, discoveries, avatar/room customization, focus tools | Coherent art and a place for a character matter. A full 3D room and music platform are outside our budget and stack. |
| [Finch](https://help.finchcare.com/hc/en-us/articles/37935669335309-Our-Approach-to-Self-Care) | A customizable bird linked to small real-world goals | Design encouragement around chosen actions. Do not claim therapeutic benefit or turn work into a compulsory streak. |
| [Tamagotchi Paradise](https://tamagotchi-official.com/us/series/paradise/howto/) | Care influences growth; characters and variations can be collected | Stable identity plus some variation can provide discovery. Do not make a work companion sick or unhappy when its owner is absent. |
| [VS Code Pets](https://tonybaloney.github.io/vscode-pets/pets/) | Named pets, simple play, friendships, export/import | Developer workflows are a plausible setting; bounded playful interaction can be enough. Its existence alone does not validate productivity gains. |
| [VPet](https://github.com/LorisYounger/VPet/blob/main/README_en.md?plain=1) | Windows pet with many authored animations and mod support | Expressiveness requires content production, not merely an animation timer. Its WPF implementation is not a reason to replace Qt. |
| [Desktop Goose](https://samperson.itch.io/desktop-goose) | Deliberately disruptive cursor stealing, notes, and desktop antics | Strong personality can also be incompatible with focused work. Borrow distinctiveness, never input interference. |

As a qualitative check, Desktop Goose's own comment pages contain both affection and requests for help disabling cursor interference or closing the app. These are a convenience sample, not a measured dissatisfaction rate. They are useful failure scenarios: the companion must be easy to quiet, hide, and exit. [User comments](https://samperson.itch.io/desktop-goose/comments?after=2108).

### What psychology supports, with limits

The original IKEA-effect experiments found higher valuation for successfully self-assembled objects; unfinished work did not produce the same benefit. A later meta-analysis covering 55 studies and 5,454 participants reports a moderate average valuation effect. That supports testing a short, successful customization experience. It does **not** establish that more effort is better or predict seven-day retention for FlowPilot. [Original research](https://dash.harvard.edu/entities/publication/73120378-ce76-6bd4-e053-0100007fdf3b), [meta-analysis](https://doi.org/10.1002/mar.70064).

A human-agent study reported increased empathy after robot assembly. Its physical assembly task is not equivalent to picking a digital hat. Treat it as supporting a hypothesis about participation, not proof of a relationship with our characters. [Study](https://arxiv.org/abs/2312.11781).

Self-determination research offers autonomy, competence, and relatedness as useful design lenses. A subsequent HCI review explicitly criticizes shallow applications of that theory. For us: allow meaningful choice, make completion easy, and test whether people actually care. Do not advertise a scientifically proven attachment or productivity system. [Motivational model](https://selfdeterminationtheory.org/SDT/documents/2010_PrzybylskiRigbyRyan_ROGP.pdf), [critical review](https://arxiv.org/abs/2405.12639).

## 3. Demand reality and the narrow audience

Known first-party evidence is limited: the founder likes the cat, finds the other appearances less appealing, and wants the companion to be desirable in its own right. We do not yet have independently verified numbers of regular users, requests for companions, conversion, willingness to pay, or retention. None should be invented in a pitch.

Primary hypothesis: adult Windows developers and technical writers who already personalize their desks/editors and have a genuine dictation use case. They may enjoy a companion but still care intensely about privacy, accurate identifiers, and focus.

Secondary research cohort: adults already using cozy desktop games or virtual pets. They can test character appeal, but their enthusiasm must not be counted as demand for voice software.

Not the initial target: children, enterprise buyers who prohibit decorative software, or everyone who buys collectibles. Parents can be part of the adult audience without turning this into a child-directed product.

Likely alternatives include ordinary dictation with no mascot, VS Code Pets, a desktop game, or simply no companion. Ask participants what they actually use; do not assume they need all these products combined. The most consequential unknown is whether the audiences overlap enough to justify one product.

## 4. The proposed product: adopt first, create second

### The experience we should aim for

Someone sees a ten-second clip and likes the character without needing to know what model powers transcription. On installation they can try useful dictation immediately or choose a companion. In about a minute they name it and make a few good-looking changes. It responds clearly while they dictate and settles when they stop. A week later it still feels like their character, not an animated advertisement.

Working positioning: **Private dictation. A little character of your own.** This is copy to test, not a claim of validated differentiation.

### First-session sequence

1. Present Signal, the existing cat, and the new original companion without forcing a choice before dictation works.
2. For the original, offer six curated palettes, three expressions, and four compatible accessories including none. Show a finished result immediately.
3. Let the user name it, see listening/working/recovery poses, and optionally choose a restrained behavioral style.
4. Save to the library. Activate only through an explicit Apply action; Cancel must not silently replace the current companion.
5. Show one useful next action: try dictation in the user's chosen editor. Never insert demonstration text without their action.
6. Offer a shareable character card later, on request, not a first-run social prompt.

The proposed option counts are scope limits, not research findings. A small curated set is preferable to hundreds of combinations with inconsistent quality.

### Character direction and an art acceptance test

Prepare three distinct original concept studies, not three finished feature sets:

| Concept, working description | Character appeal hypothesis | Signature action to test |
| --- | --- | --- |
| Pilot, the pocket courier | Helpful, capable, slightly earnest; fits FlowPilot's name | Holds a small parcel while working, gives a restrained acknowledgement on verified completion |
| A sleepy seed creature | Soft, grounded, quietly amusing; less technological | A leaf lifts attentively during listening and settles afterward |
| A little cloud creature | Expressive silhouette, soft visual presence | A small internal glow or face change, not constant floating across the desktop |

These are unproduced concepts, not cleared names or committed additions. Test them against the existing cat and Signal. If the cat wins, that is useful evidence; do not force a robot because it matches the brand name.

Judge art at actual desktop size, on a busy editor, before approving enlarged illustrations. Require a recognizable silhouette, readable face, consistent palette, five functional poses plus neutral uncertainty, and a memorable but restrained idle action. Accessories must not hide state feedback. Avoid near-copies of recognizable franchise characters, tracing, or branding that suggests endorsement.

Authored quirks should convey personality without pretending to understand private work: a courier straightens its parcel; a seed creature adjusts its leaf. No claims that it knows the user is stressed, lonely, coding badly, or working hard.

## 5. The loop that could make it worth keeping

### Core loop for the first release

Choose → personalize → use real dictation → see accurate, restrained feedback → return to the same character. A new accessory is optional expression, not a requirement to keep a pet happy.

Success animation must follow **verified insertion**, not merely completed transcription or dispatched keystrokes. Sent-but-unverified gets a neutral state. Failure offers recoverable text without a sad animation that pressures another attempt. Aesthetic feedback must never conceal technical uncertainty.

### Collection without a slot machine

If the basic companion survives a week of use, test a tiny themed shelf in Studio: perhaps a desk lamp, scarf, and mug. Let people choose items directly. A user-requested surprise selection may reveal an already-owned item, with immediate change/undo; no payment, rarity odds, duplicates, or scarcity claims.

Do not reward microphone-on time, word counts, keystrokes, streak preservation, or meaningless dictation. These incentivize behavior that conflicts with useful software. Do not punish absence or delete progress. Prefer small authored discoveries during intentional Studio visits, and make all cosmetics obtainable without work quotas.

The shelf belongs in Studio, not as a persistent expanding obstruction on the desktop. Start with one visible companion; several simultaneous pets create another rendering, interaction, and distraction problem.

### Share the object, not the person's work

A character card can show art, a user-chosen public name, and optional creator credit. It must not capture the desktop, window title, transcript, workplace identity, local path, or usage statistics. Show an exact export preview and allow removing the name. Sharing is a local file export; posting remains the user's choice.

A future editable recipe gives creators something to exchange beyond a screenshot. Do not add a public upload gallery until import safety, rights reporting, moderation ownership, and ongoing support are funded.

## 6. What kind of creator to build

| Route | Benefit | Cost / limitation | Decision |
| --- | --- | --- | --- |
| Curated local parts and palettes | Immediate attractive results, reproducible poses, no network or generation model | Needs original art and compatibility rules | Recommended first |
| Existing manual pixel editor | Full authorship for enthusiasts | Drawing and animation are substantial work | Keep as an advanced path, not required onboarding |
| Emoji/image import | Fast reuse of something the user already owns | A still image is not automatically a well-animated character; rights vary | Keep; explain limitations honestly |
| On-device generative image model | Broader prompts and variation | Model distribution, hardware testing, coherent animation, moderation and licensing need separate investigation | Defer; no promise of good CPU-only results |
| Cloud prompt-to-character service | Potentially broad creation options | New network/data boundary, recurring cost, policy conflict | Exclude from this local-first proposal |

A creator needs more than combinations: Undo, reset, accessible labeled controls, compatibility checks, a preview at real size, editable saved choices, and a reliable way to keep the result. The strongest initial design is guided finishing of good artwork, with advanced creation available afterward.

## 7. Architecture that fits the existing project

### Reuse before adding systems

The local code already has Companion Studio, emoji/image/sprite imports, `.flowpack` sharing, a 16×16 three-frame pixel editor, a companion store, and Gemini's in-progress shared renderer. This is not a greenfield creator. Reuse these surfaces after their contracts are verified.

| Existing area | Observed condition | Proposed change in a later implementation |
| --- | --- | --- |
| `ui/companion_renderer.py`, HUD and preview | Shared renderer exists in the worktree | Agree on the finalized API with Gemini; do not introduce another rendering path |
| `ui/pixel_creator.py` | Saves under `Path.home()/.flowpilot`, writes assets directly, and immediately changes the active selection | Use the configured asset manager and separate library save from Apply |
| `engine/companion_assets.py` | Source bounds include 512×512, 1 MiB per PNG, and 12 frames in sprite creation | Validate all entry paths; keep bounded recipes and assets, not unlimited generated animation |
| `.flowpack` import/export | Current code limits archive size and checks member names; extracts before all content checks; export removes a top-level directory field | Add decompressed-size/member-count caps and strict schema/export allowlists before promoting community sharing |
| `engine/companion_store.py` | Existing local persistence and selection | Extend with versioned, backward-compatible recipe references, not a second independent settings database |

These are source observations, not an executed exploit assessment or a claim that every custom frame/state currently renders correctly.

### Proposed data and event contract

Keep the current image/spritesheet runtime representation initially. Add versioned, validated recipe metadata only after compatibility tests: template ID/version, palette ID, expression ID, accessory IDs, optional display name, and bounded behavior preset. Use identifiers into shipped definitions, never imported Python expressions, executable plugins, remote URLs, or absolute paths.

Export an allowlist of public recipe fields and approved artwork/license files. Keep local identity, creation history, preferences, and any research counters separate. Imported recipes cannot alter hotkeys, microphone policy, history settings, or application preferences.

Compile a selected recipe into a bounded set of cached frames when edited, not every paint. Share normalized state, elapsed time, audio envelope, motion setting, and display scaling between preview and HUD. Fit state frames within the existing 12-frame budget or explicitly revise the format and tests; do not silently exceed it.

A deterministic behavior controller may choose among a few authored idle actions. It receives only necessary lifecycle/UI events. It does not read transcripts, clipboard contents, filenames, screenshots, or global keystrokes. Cosmetic preferences do not require an LLM or a self-learning agent.

### Microphone and focus are product boundaries

The current warm pre-roll means dictation readiness and microphone access are linked. Hiding the HUD is not equivalent to disabling capture. Do not advertise a microphone-free pet until that mode exists and is tested.

A later companion-only mode would close the recorder, disable speech-trigger behavior, and clearly indicate that dictation is off. Re-enabling dictation would require warming the recorder and showing readiness before promising pre-roll protection. This is an explicit lifecycle change, not a cosmetic checkbox.

The passive companion must remain non-activating. Deliberately opened Studio may accept input, but must not cause a later paste into the wrong window. Keep play interaction inside Studio initially: clicking a desktop character must not ambiguously mean both petting and starting the microphone. Preserve existing click/drag and appearance-lock safeguards.

### Performance and accessibility gates

Use the existing PySide6/QPainter process; no browser renderer, socket animation bridge, or new background model. Stop repainting hidden/static surfaces, bound caches, and prioritize the speech pipeline. The project's sub-0.2 ms paint and sub-5 MB incremental companion-memory targets remain unverified targets, not measurements from this research.

Measure companion-off versus Signal versus original companion on the same machine: idle CPU, incremental working set, paint duration distribution, and dictation stop-to-text p50/p95. Include long idle, rapid bursts, Studio open/closed, and multiple DPI settings. Report regressions rather than averaging them away.

Reduced motion should suppress ornamental loops, not merely whole-window bobbing. Use static shape/state cues, never color alone. Provide keyboard-accessible Studio controls, readable names, scalable previews, mute-by-default behavior, and an obvious Hide/Switch to Signal action. Do not promise screen-sharing exclusion without testing the supported capture paths.

## 8. Trust, original art, and practical production

Our differentiation should be original characters, useful behavior, local ownership, and reliable software together. A cute skin by itself is easy to copy and does not prove a defensible business.

Record provenance for every shipped asset: creator, source revision, license, modifications, and distribution notices. Code and artwork can have different permissions; VPet's repository explicitly distinguishes its code license from animation terms. Do not infer art reuse rights from a repository's headline license. [VPet licensing documentation](https://github.com/LorisYounger/VPet/blob/main/README_en.md?plain=1).

For original work, retain editable source files, a pose sheet, anchor positions, palette rules, frame timing, and written usage rights from any commissioned artist. For the existing cat, complete the exact upstream attribution/package-notice work already assigned to Gemini. Competitor screenshots and characters are research references, not assets to redistribute.

Do not grow a content treadmill before knowing whether people keep the first character. Each accessory must work across poses, scales, motion settings, and dark/light backgrounds. Track production and QA time per pack; combinatorial choice is not free content.

Keep privacy and safety independent of cosmetics. No ad trackers, automatic community uploads, transcript-based personalization, screen watching, or requirement to enable history. Cosmetic memory stores deliberate choices only. Users must be able to reset those choices separately from dictation data.

## 9. Business and distribution hypotheses

Recommended order: prove the core experience, then test optional fixed-price artist packs or a supporter bundle. Keep a good companion, Signal, privacy controls, and essential accessibility available without recurring cosmetic payment. Existing imported creations should remain usable offline. No paid random drops, forced account, or subscription required to keep a pet alive.

No price or revenue forecast is justified yet. A future pack's break-even calculation should include art, implementation, QA, support, distribution/payment costs, and refunds. For an open-source product, do not assume cosmetic sales can fund all engineering or require invasive DRM to enforce them. Packaging convenience and supporting the project may matter, but must be tested.

Use separate acquisition messages in a small pilot: (A) private developer dictation, (B) an original companion alongside useful dictation. Show the same real product. Measure useful activation and continued use, not just clicks on the character. Avoid child-targeted campaigns in this first adult pilot.

Possible later channels are developer communities, creator demonstrations, and cozy-desktop communities. Do not post or contact anyone automatically. Provide a clean Windows installation/uninstallation path and truthful unsigned/signed build disclosure; appealing artwork cannot compensate for an alarming or unreliable installer.

## 10. Validation: a practical way to discover whether people want it

### Before substantial code

Recruit, with approval, roughly 12 adults for moderated concept/usability sessions: six relevant Windows developers/writers and six existing desktop-companion/cozy-game users. This is exploratory research, not a statistically representative survey. Include people outside the founder's friends and record non-interest, not just compliments.

Ask about their last real use of dictation or a digital pet; what they kept, disabled, or paid for; and why. Show original concepts, the cat, and Signal in varied order at actual desktop size. Ask what they would install today and what they would remove after a busy hour. Do not begin with "Would you love this?"

Compare a ready-made adoption path with guided customization. A task is complete only when the person gets a result they want to keep without coaching. Identify whether they care about the character, the creator, the dictation tool, or none of them.

### Then a seven-day pilot

Aim for 20 adult Windows participants if recruitment permits; report exact denominators and cohort differences. Keep study participation optional and compensate independently of favorable answers. Test a comparable no-companion condition and counterbalance order where practical. This sample gives directional evidence, not proof of small retention or productivity differences.

Suggested decision rules below are proposed internal thresholds, not industry benchmarks:

| Question | Measure | Initial decision rule |
| --- | --- | --- |
| Can people make something they like? | Unaided save/apply, time, requested assistance | At least 9/12 concept participants finish in about 90 seconds and choose to keep a result |
| Does it survive novelty? | Day-seven voluntary choice of companion vs Signal/off | At least 12/20 pilot participants still choose the companion; report developer and cozy cohorts separately |
| Does it coexist with work? | Hide/disable reasons; observed focus errors and unwanted microphone activation | Any reproducible safety defect blocks release; recurring distraction triggers redesign, even if ratings are positive |
| Is the combined product useful? | Participants actually choosing dictation for a real task after the demo | Require evidence beyond mascot interaction; set a quantitative gate after establishing current dictation-use baseline |
| Is personalization worth its complexity? | Guided vs ready-made completion and later preference, including abandonment | If a ready-made pet performs as well directionally, ship that first and defer the richer creator |
| Is sharing wanted? | Unprompted request or deliberate card export | Treat sharing as optional discovery, not a forced growth target |

No hidden analytics. Prefer consented observation and short user diaries. Any pilot counters must be opt-in, local, inspectable, deletable, and exported by the participant; exclude audio, text, app/window identifiers, and background activity. Respect never-store settings and do not repurpose existing history for research.

Report technical results independently from desirability. A green regression gate is not a character-preference study; a loved character is not evidence of paste reliability. Stop expanding if only hobbyist pet users remain engaged and the intended dictation audience disables it.

## 11. Delivery sequence and ownership

Effort ranges are planning estimates for one engineer with an available artist, excluding recruitment delays and unknown renderer integration issues. They are not commitments.

| Stage | Deliverable / exit condition | Estimate |
| --- | --- | --- |
| A: concepts and evidence | Three pose studies, actual-size comparisons, participant sessions, selected direction | 2–4 working days plus recruitment |
| B: one polished original | Approved silhouette, functional poses, two restrained quirks, accessible static states, documented rights | 3–6 artist-days, partly parallel with engineering |
| C: guided creation | Recipe validation, reuse of asset manager/store, save vs Apply, shared preview/HUD integration | 3–5 engineer-days after renderer handoff |
| D: safety and polish | Import/export hardening, migration, failure cases, focus/DPI/motion/performance checks, current full regression gate | 2–4 engineer-days |
| E: reality check | Seven-day pilot, separated technical/desirability report, continue/reduce/stop decision | 7 calendar days plus analysis |

Tomorrow's smallest deliverable is a concept/adoption test, not a new creator framework. Do not advertise a completed companion product until authored art, integration, and validation have all happened.

Gemini retains the renderer, HUD/preview integration, Signal/Pilot realization, and attribution work already underway. A later creator implementation can own recipe validation and guided Studio flow, with shared files edited only after a handoff. Package hardening and data-lifecycle corrections should be separate reviewable changes. Do not overwrite concurrent work, commit, push, or republish without instruction.

## 12. Longer-term vision and explicit exclusions

If the first character is genuinely kept: expand into a small coherent collection, better editing, user-owned exportable recipes, transparent artist collaborations, and an explicitly microphone-off companion mode. A local character can retain its identity across versions without needing chat, emotional surveillance, or a remote account.

Defer autonomous agents, voice conversations with the pet, 3D worlds, social feeds, generative-model downloads, marketplaces, breeding economies, and physical merchandise. Each is a separate business or architecture decision, not a prerequisite to making one character lovable.

The decision requested is to approve **one original, highly polished companion with guided personalization**, validated against the cat and Signal. Research supports testing this direction. Only actual user behavior can establish whether it earns the "I want the toy too" response.

## Research coverage and limitations

Covered: adult-toy category evidence, nine product comparisons, customization/motivation research and counterarguments, adult audience selection, art and animation direction, creation options, retention and ethical collection, sharing, licensing, local architecture, security boundaries, accessibility, performance, monetization hypotheses, distribution, validation, and delivery scope.

Method: public primary product documentation/store pages, a primary market-research release, academic publications/abstracts, a qualitative comment-page check, and local source inspection. This was desk research, not an exhaustive systematic literature review. No competitor was installed or benchmarked for this study; no new customer interviews, willingness-to-pay experiment, runtime performance measurement, legal clearance, or full regression run took place. Product/vendor claims remain attributed; proposals and estimates remain unvalidated.

## 13. Parallel delivery addendum: core fixes and companion polish

Date: 2026-10-21. Status: proposed work allocation, not launched workers or approved artwork. This addendum updates delivery mechanics without representing the older research snapshots as current implementation facts.

### Current assessment and smallest useful slice

The working product has local dictation, recovery, personalization and companion infrastructure. The user reports successful F9 insertion in Notepad, VS Code and Terminal. That is valuable manual evidence, not a broad reliability or competitor-parity measurement. Language/model fixes are being edited concurrently and remain pending review.

Provisional reviewer judgment: 6/10 for product completeness, not measured accuracy, percent complete or a competitor score. Remaining priorities are truthful settings/results, real-voice multilingual accuracy, reliable insertion/recovery, approachable setup, and polished original character presentation. A higher rating needs observed independent-user task completion, not just more features or passing test counts.

The current source now has a shared `CompanionRenderer` used by preview and HUD, original Pilot/Seedling/Nimbus render paths, elapsed-time inputs and reduced-motion handling. Do not recreate those components based on older sections of this document. Source inspection also shows preview outer motion still using `_tick * 0.08`; the Pilot drawing path accepts device-pixel ratio but calculates its origin using logical integer coordinates. These are timing/scaling review targets, not a measured visual defect report. No live animation review was performed for this addendum.

The narrow deliverable is one original anime-inspired companion concept, approved at actual desktop size, with coherent state poses and restrained animation. Start with three static silhouette sketches, select one with the user, and finish only that one. Keep existing companions and Signal. A few palettes and compatible accessories are enough; a new gallery, marketplace or generative runtime is out of scope.

Required presentation states: idle, listening, processing, verified completion, sent-unverified and recoverable failure. Treat the last two honestly even if they share a neutral pose with distinct symbols. Give the character a small signature action such as adjusting a scarf or handling a message parcel. No constant jumping, cursor interference, false progress, mandatory sounds or imitation franchise assets.

### Worker ownership

| Worker | Owns | Does not own |
| --- | --- | --- |
| Gemini A: core reliability | The bounded PR 1 core reliability plan: language registration, model lifecycle, truthful transforms and their callers/tests | Companion renderer, sprites or appearance changes |
| Gemini B: companion prototype | Original concept assets, isolated deterministic preview, companion-specific tests; renderer/HUD integration only after an agreed review | STT, orchestrator, text injector, live microphone, hotkeys, release manifests |
| Codex: review and integration | Inspect diffs, challenge tests, review visual evidence, run independent checks when available, coordinate shared-file ownership and the combined gate | Unreviewed automatic merges, publishing or claiming success from a worker's summary |

Initially use two implementation workers, not many competing model/build processes on this approximately 16 GB machine. A temporary read-only QA subagent can review a bounded patch; it must not quietly become another writer of shared files. Do not assume a Codex subagent is a Gemini CLI process: these are different execution mechanisms and must be identified correctly.

### Isolation means more than different terminal windows

- Give each worker its own branch and Git worktree at a recorded baseline. Git worktrees separate working files/indexes while sharing repository data; they are not a security boundary. [Git worktree documentation](https://git-scm.com/docs/git-worktree)
- Worktrees begin from committed source, not the current dirty tree. Do not stash, reset, commit or copy all of Gemini A's unfinished edits just to initialize Gemini B. Deliberately supply the current directive files and only approved dependencies to each worker.
- Give workers separate virtual environments or controlled dependency environments, config paths, output/temp directories and test ports. Use existing `FLOWPILOT_CONFIG_DIR` / `FLOWPILOT_CONFIG_FILE` controls and unique test mutex names where supported. Inspect hard-coded home-directory writes before claiming complete profile isolation. Do not repurpose HOME or alter the user's live profile.
- Share large model weights read-only only if the loader supports explicit provisioned paths; do not duplicate or auto-download models for visual work. Animation previews receive synthetic state/audio-level values, not microphone access or transcript content.
- OS clipboard, foreground window, audio hardware, system hotkeys and common resources are not isolated by a Git branch or unique mutex. Schedule one exclusive physical-desktop test owner. Other workers use mocked hardware and offscreen Qt rendering. Never launch several microphone-owning desktop instances simply because mutex names differ.
- If stronger execution containment is required, use a separately configured VM/test account and restricted file/network access. Do not assume a VM reproduces host focus, audio or DPI behavior; those still need scheduled host validation.
- Keep existing tool approval/sandbox restrictions. No unattended privilege escalation, global installs, certificate changes, destructive cleanup or permission-bypass flags. A preview worker needs no such permissions.
- Gemini sessions may not inherit Codex's installed skills. Provide explicit task contracts and accessible instruction files; never assume saying "use all skills" automatically transfers engineering safeguards.

### Test-first and visual review sequence

1. Freeze the task's scope, owned files, baseline and observable acceptance criteria. A new file outside that ownership requires coordination, not opportunistic refactoring.
2. For behavioral changes, add a test that exercises the real production path and fails for the intended reason. Mock hardware/clock boundaries, not the method being repaired. For art, define a pose/contact sheet and visual acceptance checks before coding; a unit test cannot establish that a character is attractive.
3. Build the smallest implementation in its isolated worktree. For the companion, use the existing native renderer with injectable elapsed time, state, audio envelope and scale. Prototype code remains real code; successful review permits integration, not an unrelated rewrite in the main checkout.
4. Generate images at fixed times for all six states, dark/light backgrounds, and 100%, 125%, 150% and 200% DPI. Assert visible/nontransparent character content, bounds, state cues, reduced-motion stability and deterministic output under fixed inputs. A non-null pixmap alone is not proof that the character is visible.
5. Compare HUD and Studio presentation under equivalent inputs. Remove frame-count-dependent decorative motion and test differing repaint schedules at the same elapsed time. Use monotonic timing such as the existing [QElapsedTimer](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QElapsedTimer.html); retain crisp device-pixel placement and bounded caches.
6. Record a short animation demonstration and inspect transitions at actual size. Tests must cover unverified results not celebrating, preview-only simulated audio, reduced motion, hidden-preview timer behavior, appearance lock, click/drag separation and existing custom-companion compatibility. Repeated confirmation repaints must not endlessly restart celebration.
7. Measure companion-off, Signal and the candidate on the same host: idle/active CPU, incremental memory, paint-time distribution and impact on dictation latency. Do not quote the old sub-0.2 ms/sub-5 MB design targets as achieved without measurements. Stop needless hidden/static repaints.
8. Worker submits a bounded patch and evidence: base revision, files changed, commands/exit codes, passed/skipped/failed counts, screenshots/demo, provenance, measurements and limitations. Codex inspects and reruns critical checks; no worker may weaken tests merely to obtain a green report.
9. Integrate one reviewed change set at a time with the required authorization, then rerun affected tests and the current complete gate against the combined source. Individually green branches can still conflict. Package only a settled, reviewed candidate; do not publish automatically.

### Immediate next action

Let Gemini A finish its current bounded PR 1. Prepare Gemini B's concept/preview task in a separate worktree once its execution is requested, leaving core files untouched. Review the silhouette and state sheet before spending time on accessory combinations. Start with offline, hardware-free visual tests; reserve the real desktop for scheduled integration checks.

This addendum is a planning deliverable guided by product discovery, engineering review, spec-driven planning and the iterative test loop. No worker/terminal/VM was launched, no worktree was created, no artwork was generated and no app code was changed for it. Concurrent core changes were observed but not certified.
