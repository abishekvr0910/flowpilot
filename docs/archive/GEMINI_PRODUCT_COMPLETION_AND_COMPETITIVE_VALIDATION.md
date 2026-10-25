# FlowPilot product completion and competitive validation

Date: 24 October 2026.
Audience: Gemini, Codex, maintainers, and the product owner.
Reviewed source: `6555e3dc9cd507b5fbc31d71f3d0be95d1c4078a`, tagged `v3.1.0-RC3`.
Status: reviewed planning handoff. Implementation and evaluation remain open.

Revision 2, 24 October 2026: explicit agent instructions, verified code and test map, correction of the implementation partner's proposed microphone/timing work, and scoped correction learning. Application source remains unchanged by this documentation revision.

## 0. Start here before changing code

The proposed response that mentions "likely engine/audio.py", keeping a stream across focus changes, and timing `engine/voice_editor.py` does not describe the assigned work correctly. Use the following interpretation.

| Proposed action | Correction and exact starting point |
| --- | --- |
| Run the RC3 live test suite | `tests/run_all_tests.py --require-all` is the strict aggregate gate. It does not automatically perform every remaining manual row in [the interactive checklist](../testing/COMPANION_VISIBILITY_INTERACTIVE_GATE.md). Pin `FLOWPILOT_TEST_EXE` to the verified candidate and record its hash. Keep aggregate tests and remaining live rows separate. |
| Persist the microphone stream across focus changes | The defect under investigation is a saved numeric input index becoming a different device after enumeration changes. The real module is [audio_recorder.py](../../engine/audio_recorder.py), not `engine/audio.py`. Persist device identity and resolve its current index. A stream object is a runtime resource, not a setting to preserve across restart. Do not change focus behavior to solve device identity. |
| Time speech to text inside the voice editor | Normal F9 dictation flows through [orchestrator.py](../../engine/orchestrator.py), [stt_engine.py](../../engine/stt_engine.py), [context_processor.py](../../engine/context_processor.py), and [text_injector.py](../../engine/text_injector.py). `voice_editor.py` plans bounded edits, not normal dictation delivery. Actual delivery needs an independent target document observer. |
| Put latency percentiles in CSV | CSV is an optional report format, not proof of the timing endpoint. Keep trial identity, outcome, timing boundary, missing observations and raw durations. Compute summaries only from correctly classified trials. Preserve the current `not_measured` value when no target observer exists. |
| Ask the owner which module or action to start with | The starting order is already specified: P0 evidence and remaining live rows, P1 device identity, then P2 observed delivery. Inspect the repository before asking for information it contains. Only a concrete missing resource or decision should block the dependent work. |

### Agent instructions to load

Read [root AGENTS.md](../../AGENTS.md), [engine/AGENTS.md](../../engine/AGENTS.md), [ui/AGENTS.md](../../ui/AGENTS.md), and [tests/AGENTS.md](../../tests/AGENTS.md), then recheck for more specific instructions in any directory you will change. These are active engineering contracts. This handoff does not replace the agent's system, developer, workspace permission, or current user instructions.

Use the applicable skills in their actual installed locations: scope for the feature register, architect for unresolved device/observer design, develop for the agreed slice, debug for a reproduced failure, check for behavior and review, test for meaningful regression coverage, and sync/document when their change types apply. Read a skill before claiming to follow it. Installing unrelated tools or invoking every available skill is not required. Missing skills or unavailable desktop tools should be reported accurately.

| Agent rule | Required behavior for this work |
| --- | --- |
| Preserve workspace work | Record `git status --short` and `git rev-parse HEAD`; inspect current changes. Preserve unrelated work, the untracked research note, existing release tags and artifacts. Do not reset, discard, stash or bulk stage them. |
| Environment before imports | Stage isolated `FLOWPILOT_CONFIG_FILE`, `FLOWPILOT_CONFIG_DIR`, unique `FLOWPILOT_MUTEX_NAME`, and appropriate `FLOWPILOT_HEADLESS`/`FLOWPILOT_NO_POPUP` before importing engine modules. Use synthetic/headless mode only for the corresponding tests, never as physical evidence. |
| Import side effects | Do not import `engine.server` or construct an orchestrator merely to discover symbols; they can start model/hotkey work. Read or parse source for the code map. |
| Process isolation | Python child commands use `-X utf8`; Python subprocess calls explicitly pass `encoding="utf-8", errors="replace"`. Launch background helpers hidden. Close only owned test processes by their recorded PID/handle; never terminate all Python, Notepad or FlowPilot processes by name. |
| Qt ownership | Keep blocking capture, recognition, model and Windows audio/accessibility calls off the GUI event loop. Engine status reaches UI through `StateBridge`; passive HUD focus remains protected. Intentional settings and editor windows still accept input. |
| Companion ownership | `CompanionVisibilityController` remains the sole owner of HUD presentation. Do not fix a test by calling `hud.show()` or `hud.hide()` from unrelated handlers. |
| Delivery truth | Preserve `InjectionResult` and `InjectionStatus`. Unknown focus must not authorize dispatch. Safe abort, unverified dispatch and confirmed insertion remain different outcomes. |
| External editing | External transform Replace/Revert remain disabled. A caller supplied target label does not establish a valid selection or revision. Scratchpad uses its existing transactions. |
| Local processing | No new cloud inference, telemetry upload, proxy bypass or silent model download. An optional loopback integration does not authorize remote forwarding. No competing web renderer or IPC UI bridge. |
| Code conventions | Touched/new Python modules use a feature or PR numbered opening docstring and `logging.getLogger("FlowPilot.<Module>")`. Do not introduce raw transcript/audio logging. Prefer small helpers over growing already large orchestrator/UI files. |
| Test integrity | New suites follow `tests/AGENTS.md`, bootstrap the project import path, stage env early and are connected to the runner where appropriate. Keep real warmup/switch logic exercised while mocking hardware boundaries. Never force success, remove skip guards, or replace physical insertion with a hidden test rescue. |
| Package identity | Source tests and packaged tests validate different artifacts. Build changed source into an isolated candidate before packaged verification; do not test an old executable and attribute its result to new code. |
| Live desktop | Run only with a verified interactive, idle desktop and isolated fixtures. Do not infer that a past idle confirmation still applies. Continue read only work and unit checks if the desktop is busy; record missing physical evidence honestly. |

Historical status lines in AGENTS files do not erase newer dated evidence: RC3 has the recorded Edge/PowerPoint/F9 checks, whereas RC2 did not include the feature. The underlying rules remain binding. Flag stale context for a narrow update; do not rewrite curated instructions to bypass a gate.

Before P1 or P2, write the feature specification with the actual call sites, data contract, failure behavior and tests described in section 16. Names for proposed helpers are proposals until that spec is recorded. No implementation is claimed by this handoff.

For a physical run, use a disposable test process with `FLOWPILOT_HEADLESS` absent, not the string `"0"`; some paths test whether the variable exists. Do not force a headless/offscreen Qt platform for that run. Clearing a flag does not grant access to the Windows input desktop: verify actual desktop and foreground access separately. The runner already creates isolated config files per suite, while direct test launches need equivalent env staging. Record the exit code and keep complete logs under an isolated local evidence directory.

## 1. What you are trying to achieve

Make FlowPilot the preferred Windows dictation tool for developers who want accurate words, reliable delivery, understandable recovery, and local processing. Let original companions make the product enjoyable without interfering with work.

The first competitive objective is less time to correct, usable text than Wispr Flow on declared Windows developer tasks, without worse factual errors or unsafe delivery. English, Hindi, Tamil, and Malayalam are the priority languages. Support for each language needs its own evidence, including speech that mixes that language with English technical terms.

There are three separate completion decisions:

1. **Engineering complete:** the agreed behavior is implemented and its acceptance checks pass.
2. **Release ready:** the exact packaged bytes pass product, privacy, upgrade, hardware, and pilot gates.
3. **Competitive advantage demonstrated:** a fair comparison supports a specific claim for the tested tasks, languages, machines, and versions.

None implies the other two. A completed experiment can honestly conclude that Wispr wins, FlowPilot wins only some tasks, or the evidence is inconclusive.

"100% better than Wispr Flow" is not a testable product requirement. It could mean twice as fast, half as many errors, or superiority in every feature, which are different claims. Do not use it. The final claim should name a measured outcome, sample, date, and limitation. This document cannot promise the eventual result.

## 2. Document authority and limits

The living feature register is [scope/index.md](../scope/index.md). This handoff supplies the complete execution and evidence plan, not a replacement architecture specification. Existing [engineering boundaries](CODEX_DIRECTIVE.md), `AGENTS.md`, and [spec 0001](../specs/0001-context-aware-companion-visibility.md) remain in force.

Use this handoff to supersede stale completion and priority statements in earlier handoffs. Preserve dated measurements as historical records. Resolve architectural changes in `docs/specs/` before building them. Numerical gates below are proposed engineering targets, not achieved measurements or a change to an existing release tag. Freeze them in the evaluation specification before examining final results.

The review read current scope, relevant engine and UI paths, release records, local live JSON records, corpus reports, and exact commit CI status. It did not replay every historical log, rerun every feature, or conduct an independent security certification. No new live input tests were run while preparing this document.

## 3. Evidence at the reviewed baseline

| Area | Evidence available | What it does not establish |
| --- | --- | --- |
| Source and remote CI | RC3 source is `6555e3d`. [Run 40006224097](https://github.com/abishekvr0910/flowpilot/actions/runs/40006224097) succeeded on that commit. The recorded hosted accounting is 47 passed, 7 headless skips, 0 failed. | Hosted skips do not validate physical input or focus. |
| Local release gate | [RC3 manifest](../release/RELEASE_ARTIFACT_MANIFEST.md) and [live validation](../testing/MEDIA_AUDIO_PRESENCE_VALIDATION_2026-10-23.md) record 54 passed, 0 skipped, 0 failed in 175.07 s. | This is recorded release evidence, not a fresh suite run for this handoff or universal reliability proof. |
| Packaged identity | Executable SHA-256 `D17FEC1C94918520CAF51B3F250897875671B6BB0B401429315AA08999ABF52E`; archive SHA-256 `FEB13D469622B53DFD4D3B54BC8ED7C90A47DADA4B32BC1EA7432992A89C340C`. | Future edits or signing do not inherit these hashes. |
| Size and signing | ZIP 772,950,120 bytes; full unpacked app 1,111,645,305 bytes. Base and small weights are bundled. Current candidate is unsigned. | Launcher size alone is not installed size; an unsigned pilot is not publisher verification. |
| Live media behavior | Local Edge video: audible hide 2.141 s, mute restore 2.068 s, unmute hide 1.414 s, pause restore 1.717 s. | This detects audio, including music. It does not identify a video, and muted windowed video does not trigger it. |
| Fullscreen and presentations | Edge F11 hide/restore 0.556/0.706 s; PowerPoint slide show 0.607/0.746 s. | Not every browser, monitor arrangement, or presentation application was tested. |
| Hidden dictation | F9 inserted the expected phrase once in Notepad while the HUD stayed hidden on the successful trial. An earlier focus loss attempt was not counted as a pass. | Not a test of every tray state, target app, or repeated real user session. |
| Display fit | Repaired candidate fit the primary 125% and secondary 100% work areas. | Secondary packaged evidence is geometry; an occluded screenshot was discarded. This is not every page at every DPI. |
| Priority language corpus | [Development report](../evaluation/DEV_SMOKE_EVAL_REPORT.json): 40 requested items, 0 evaluated, 40 missing audio, metrics null. | Language registration and a template do not prove English/Hindi/Tamil/Malayalam quality. |
| Other real speech | [DE/ES/FR baseline](../evaluation/DE_ES_FR_REAL_VOICE_BASELINE.md): 120 Common Voice clips per model. Local raw reports exist in `scratch/evaluation/desfr_base.json` and `desfr_small.json`. | Read speech in these languages does not validate spontaneous speech in the four priority languages. Small improved accuracy but decode p95 was about 2.33 to 2.42 s on that host. |
| FlowPilot timing | [Runtime protocol](../testing/RUNTIME_PERFORMANCE_PROTOCOL.md) separates processing and injection result from actual visible delivery. Production visible delivery remains explicitly unmeasured. | Processing p95 is not time until text appears. |
| Wispr comparison | [Research note](../research/COMPETITIVE_WISPR_FLOW_ANALYSIS_2026-10-23.md) reports 1,847 internal history latency records, with mean 906.6 ms under Wispr's own field definitions. | The aggregates have different inputs and unknown comparable boundaries. They cannot rank the two products. No new access to a Wispr database is needed for this plan. |
| Matched comparison | [Existing protocol](../testing/WISPR_FLOW_HEAD_TO_HEAD.md) has no completed comparable live paired results. Its 15 fixture results are FlowPilot processing only. | They are not a victory over Wispr. |
| Device selection | Settings saves `audio_device_index`; orchestration and scratchpad consume it. Live trials used changing PortAudio device numbers. | This supports a persistence risk, not a newly reproduced wrong microphone incident. |

Local supporting records include `scratch/release-live-fixtures-20261023/edge_trial.json`, `presentation_trial.json`, `f9_trial_rc3.json`, `packaged_layout_trial.json`, and `rc3-selftest-final.stdout.txt`. They are ignored local evidence, not guaranteed to be available in a fresh checkout. Future release records should include a sanitized, tracked evidence index and full hashes of retained private artifacts. Do not publish participant audio or private logs merely to make evidence portable.

## 4. What the competitor actually sets as the bar

The following are vendor documented capabilities, checked on 24 October 2026, not independent performance measurements:

| Outcome | Documented Wispr behavior | FlowPilot response |
| --- | --- | --- |
| Natural speech becomes readable writing | Formatting, spoken punctuation, and conversational self correction are documented. [Formatting and Backtrack](https://docs.wisprflow.ai/articles/5373093536-How-do-I-use-Smart-Formatting-%26-Backtrack) | Evaluate existing correction and formatting engines on ordinary, ambiguous, and mixed language speech. Do not rebuild an already present feature. |
| Useful words land in the right app | Windows clipboard paste, adaptive restore delays, and app limitations are documented. [Accuracy and limitations](https://docs.wisprflow.ai/articles/4048537120-what-to-expect-from-flow-accuracy-and-known-limitations) | Compare observed delivery and recovery. Do not assume a proprietary insertion method guarantees success. |
| Personal terminology and reusable phrases | Desktop dictionary corrections, snippets, search and shared entries are documented. [Dictionary and snippets](https://docs.wisprflow.ai/articles/9639977157-view-shared-dictionary-words-and-snippets-in-the-admin-portal) | Verify existing local aliases, scopes, snippets, imports, and immediate updates. Team cloud sync is outside this release. |
| Spoken edits | Desktop Command Mode edits text, with account eligibility and experimental settings. [Command Mode](https://docs.wisprflow.ai/articles/4816967992-how-to-use-command-mode) | Keep scratchpad transactions working. External editing remains unavailable until a real target adapter can verify revision and selection. |
| A coherent app | The Hub exposes Home, Meetings, Dictionary, Snippets, Settings, and Help, with plan dependent availability. [App navigation](https://docs.wisprflow.ai/articles/5096240724-navigating-the-wispr-flow-app-desktop-ios-and-android) | Verify an original native workflow across every FlowPilot surface, not visual imitation alone. |
| Privacy choices | Wispr performs transcription in the cloud and offers separate data controls. [Data controls](https://wisprflow.ai/data-controls) | Prove local execution and local retention behavior. Do not claim that Wispr has no privacy controls or that offline operation alone certifies regulated use. |

Do not claim that offline dictation or a desktop pet is unique across the market. [Superwhisper advertises offline Windows dictation](https://superwhisper.com/windows), and [Aqua Voice advertises a customizable pet](https://aquavoice.com/pet). Our hypothesis is that dependable private dictation plus original, user created companions is valuable. User trials must establish that value.

## 5. Complete scope coverage

This matrix covers every current scope ID. "Verify" means finish evidence for existing code; it does not imply that code is absent.

| Scope IDs | Product area | Work and acceptance boundary |
| --- | --- | --- |
| 1, 2, 28 | Capture, input device, hotkeys, sessions | Preserve pre-roll, route the selected input reliably, support F9 and configurable keys, recover from device loss, cancel safely, and keep repeated sessions ordered. |
| 3, 5, 15 | Recognition, languages, writing, vocabulary | Real speech evaluation; native scripts and intentional language mixing; explicit translation; aliases, negative matches, scoped prompts, deliberate corrections, numbers and identifiers. |
| 4, 16 | Delivery and recovery | Verified focus, actual document observation, no duplicate blind retries, clipboard sequence protection, truthful uncertainty, explicit Paste Last and Copy Last. |
| 6, 26 | Current voice editing and transform safety | Scratchpad revision and selection transactions, preview/apply/undo, cancellation and stale result rejection; external Replace/Revert remains disabled. |
| 7, 19 | Setup, settings, dashboard, whole app UX | Every control and navigation route; scrolling and keyboard access; truthful readiness, scaling, errors, recovery, and first use without maintainer help. |
| 8, 12 | Scratchpad, history, insights, storage | Separate retention scopes, correct opt in, deletion and migration; honest empty states and statistics; no dictated content in normal diagnostics. |
| 9 | Meeting notes and translation | Start/pause/stop, source selection, long sessions, truthful summaries and timestamps, edit/export/delete, separate consent and storage. No invented speakers or decisions. |
| 10, 20, 21, 27 | Companions and creator | Original art, all status poses, creator import/export, safe bounds, reduced motion, fullscreen/audio policy, per app rules, restart persistence, no focus theft. |
| 11, 18 | Optional local API, security, claims | Off unless enabled, loopback binding, authentication, origin and request limits, safe uploads, local model backend checks, dependency and asset notices, honest claims. |
| 13, 17 | Candidate artifacts and distribution | Exact source/build identity, complete bundle size, offline provisioning, publisher decision, fresh and upgrade profiles, rollback limits, final byte verification. |
| 14, 25, 29 | Pilot, runtime, comparison | Consent, defined machines, observer timing, fair paired tasks, uncertainty, resource budgets, pilot outcomes, and a bounded competitive conclusion. |
| 22 | Later external editing | One supported editor adapter first, with revision and selection revalidation, preview, safe apply and undo. No general external editing claim now. |
| 30 | Later optional writing context | Evaluate bounded, expressly enabled field context after the core pilot. Exclude secure fields, persist nothing, and fall back to ordinary dictation within a total 500 ms acquisition budget. App category profiles do not establish this capability. |
| 31 | Later approved correction learning | Extend explicit teaching and local preferences only after the core evaluation. Remember approved correction rules with scopes, preview, undo and deletion. No passive capture or autonomous agent actions. |
| 23 | Later editor presence | Optional local editor integration only after the core pilot. No project content collection by default. |
| 24 | Closed video recognition research | Manual app rules remain the precise fallback. Audio presence is a separate heuristic. Muted video recognition and screen sharing guarantees are not implemented promises. |

Windows developer dictation is the first release boundary. Mobile clients, cloud collaboration, autonomous tool execution, workspace surveillance, and a claim of parity with every Wispr feature are outside it. Additional languages and the later rows can expand through their own acceptance gates. They are not silently counted as complete.

## 6. Delivery order and independent gates

| Stage | Scope | Recommended output | Completion evidence |
| --- | --- | --- | --- |
| A. Reconcile and finish RC acceptance | 19, 20, 27, 18 | One current evidence ledger; completed remaining live rows | Exact build, real observations, unresolved rows retained |
| B. Stabilize input | 1, 2, 28 | Persistent device identity and safe migration | Reorder, reconnect, missing device, restart and active session tests |
| C. Make outcomes observable | 16, 25, 29 | Benchmark document observer and outcome logger | Timestamp calibration, deliberate failure cases, no dispatch treated as visibility |
| D. Collect and measure real speech | 3, 5, 15, 29 | Consented development and held out corpora | Complete per language measurements, unchanged frozen final cases |
| E. Improve the measured weaknesses | 3, 4, 6, 7, 19 | Small changes tied to error categories | Gains on development data and a fresh held out evaluation |
| F. Finish product and trust checks | 8, 9, 10, 11, 12, 17, 18, 21 | Verified journeys, privacy, assets, upgrades and package | Controls matrix, privacy matrix, real machine results |
| G. Run the pilot and comparison | 14, 29 | Pilot report and bounded comparison | Counts, losses, confidence intervals, preference and correction effort |
| H. Release decision | 13, 17, 18 | New exact candidate, reviewed release record | Strict local gate, exact commit CI, final bytes, signoff |

Stages A and B are the next work. Draft the measurement design for C while device work proceeds. Start consented recording recruitment early; do not fill missing speech with synthetic passes. UI and asset review can run independently, but should not postpone delivery and accuracy work. Any parallel work should use isolated profiles and separate branches, with one integration owner and one desktop test operator. No simultaneous tools may compete for F9 or the microphone.

### A. Close the remaining live acceptance rows

Use the [interactive checklist](../testing/COMPANION_VISIBILITY_INTERACTIVE_GATE.md) and spec 0001. Preserve the successful RC3 records and test only missing or affected behavior.

| Remaining row | Required observation |
| --- | --- |
| Chrome F11 | Test Chrome specifically; Edge evidence is not a Chrome run. |
| Restart persistence | Hide, Always, Smart, selected asset, position and app rules survive quit and relaunch. Test a fresh profile and a copied older profile. |
| Studio app rules | Normal/Edge/Hidden changes apply, cancel does not apply, removing a rule restores default behavior, and the selected character remains intact. |
| Reduced motion | Hide/restore and state transitions keep frames static where specified; hidden animation timers stop. |
| Hidden tray feedback | Listening, processing, confirmed, unverified and recoverable failure remain distinct when the HUD is hidden. |
| Multiple monitors | Fullscreen video on one monitor while editing on another follows the documented global policy without flashing or focus theft. Geometry fit alone does not close this row. |
| Media boundaries | Audible and muted browser playback, music, short notification sounds, quiet gaps, dictation, manual modes and app rules follow their priority rules. |

For each row record a direct observation, target versions, build hash, settings, expected outcome, actual outcome, and retained evidence location. If focus is unavailable, record unmeasurable or blocked. A unit test may establish policy logic but cannot substitute for a physical interaction result.

### B. Fix persistent microphone identity

Design a Windows input identity that survives enumeration changes. Resolve it to the current capture device at runtime. A display name alone is insufficient when identical microphones or multiple audio APIs expose the same name. Keep the chosen device and the current runtime index distinct.

Cover Settings, setup wizard, normal dictation, scratchpad command recording, and any other input selector. Audit meeting source selection separately rather than assuming it uses the same route. When migrating an old numeric choice, avoid guessing if identity cannot be established. Offer an explicit confirmation or system default selection and show the active input clearly.

Acceptance cases: reordered indexes; two identical names; unplug/replug; device disabled; default device changed; restart; sleep/resume; selected endpoint missing; access denied; deferred switch during recording; switching back to system default; preserved captured frames; failed replacement stream; quit during pending switch. No recording deadlock or silent fallback to a different input. A stream failure should leave a truthful unavailable state and a recovery path.

Paths to inspect: `engine/audio_recorder.py`, `engine/orchestrator.py`, `engine/config.py`, `ui/settings_dialog.py`, `ui/setup_wizard.py`, and `ui/scratchpad_view.py`. Reuse existing lock, deferred switch, and frame preservation logic instead of replacing the recorder wholesale.

### C. Observe actual text delivery

Extend the [runtime protocol](../testing/RUNTIME_PERFORMANCE_PROTOCOL.md) and existing evaluator. Keep the observer in benchmark tooling unless a separately reviewed product requirement needs it. No background monitoring of users' ordinary editor content.

Use owned test documents with a recorded baseline, target identity, cursor/selection, expected output region, and session ID. Confirm a new document change, not merely the presence of a phrase left from an earlier trial. A wrong transcription is still a delivered output: timestamp the new text independently of whether it matches the reference, then score its accuracy separately. Record first appearance and settled completion, since incremental output is not complete output.

Log the stop action, acoustic endpoint when known, actual first appearance, settled delivery, and corrected acceptance separately. Calibrate observer polling resolution and overhead. Use the same observation method for both products in each target. If a target is unreadable, mark delivery unverified; a designated human observation or consented test capture is separate evidence, never an invented automatic confirmation.

Use bounded accessibility calls outside the GUI thread. An abandoned future is not cancellation of a blocked native call. The design should isolate or contain such calls and bound resource growth. Do not add broad desktop scraping to achieve timing.

Outcome categories: verified first delivery, unverified dispatch, safe refusal, timeout, wrong target, partial delivery, duplicate delivery, successful explicit recovery, failed recovery, and cancelled. Recovery does not turn a failed first attempt into a first attempt success. Do not press Enter on arbitrary terminal content; use an owned harmless input target for terminal trials.

## 7. Fair comparison design

### 7.1 Freeze the experiment before looking at the final results

Record both app versions and plans, model hashes and parameters, dictionaries, writing styles, translation setting, Windows and target versions, CPU/RAM, power mode, network conditions, microphone route, and exact build hashes. Verify that the Wispr account can use the compared features without a quota or plan restriction invalidating the run.

Use identical consented WAVs through the same verified virtual audio route for controlled acoustic comparisons. Resolve endpoints by identity on every run. Do not change ordinary system audio defaults. Test real microphones separately, since virtual cable playback does not evaluate room capture or mic hardware.

Compare default experiences and configured developer experiences as separate conditions. Give each product equivalent legitimate vocabulary preparation. Do not tune only FlowPilot on the final test utterances. Randomize product order; preserve the random seed and failed attempts. Do not run both tools' dictation listeners at once.

Wispr needs normal internet for the primary comparison. Measure disconnected operation as a separate capability test; deliberately taking it offline cannot establish superior connected latency. Wispr receives only fixtures explicitly consented for its cloud processing. The FlowPilot evaluation remains offline. The local corpus schema's FlowPilot offline rule does not authorize sending recordings to a competitor.

Protocol interception, credential access, copied competitor source, and token extraction are unnecessary for this comparison and are outside this work.

### 7.2 Corpus stages and speaker coverage

1. **Tool smoke:** complete the existing 40 item development manifest with real recordings, or keep missing items explicitly incomplete. This validates the tooling, not language superiority.
2. **Development baseline:** target at least 100 unique utterances per priority language from at least 5 consenting speakers. Include accents, spontaneous speech, English technical terms, low volume, typing/fan noise, quantities, corrections and rapid bursts. Track these groups separately.
3. **Final claim evaluation:** target at least 200 previously unseen utterances per claimed language from at least 10 speakers not used to tune the release. Ensure substantial critical fact and identifier coverage. These are starting sample goals; if uncertainty remains wide, collect more data or narrow the claim. Replaying one speaker does not create independent speakers.

Keep development and final evaluation speakers disjoint. Reference transcripts should describe what was actually spoken. Desired formatted text should be independently reviewed and preserve intended meaning, including deliberate self corrections. Maintain exact case sensitive identifiers as annotations. Native speakers review Hindi, Tamil and Malayalam references and language mixing; English reviewers cannot certify those languages alone.

Spoken word error, character error and formatted quality use their respective references. Do not describe a lower cleaned WER against a different reference as a percentage improvement in acoustic recognition. Failed recognition is recorded as failure, not excluded or assigned the reference text. Preserve meaningful Indic combining marks and specify normalization.

Real DE/ES/FR data remains useful for model research. It does not fill missing priority language slots. No model fine tuning is planned until the error analysis identifies a failure that vocabulary, decoding, capture, or formatting changes cannot address. Any future training uses separately consented data and an untouched evaluation split.

### 7.3 Target and hardware matrix

| Dimension | Minimum initial coverage | Boundary |
| --- | --- | --- |
| Windows targets | Notepad, VS Code, Chrome editable field, Word, Windows Terminal | Record exact versions and field type. If unavailable, mark pending rather than substitute a simulated app as a pass. Add Slack or another slow app in the pilot. |
| Hardware | A documented reference developer PC and a second machine with lower resources | Record actual CPU and RAM; a CPU family label is not a support guarantee. Include a laptop microphone and a USB/Bluetooth input in capture tests. |
| Model | Base default and small quality candidate evaluated separately | Lock the production candidate before final comparison. Never combine the faster model's latency with the more accurate model's WER. |
| Delivery | At least 50 warm trials per target and hardware configuration initially | Include normal and stress cases as separate strata. Record cold launches separately. Shared fixtures are not extra independent accuracy samples. |
| Stress | Focus change, slow app, busy CPU, locked clipboard, user copy during hold, rapid sessions, cancel, elevated target, sleep/resume | Safe refusal is valid safety behavior but is not successful delivery. |
| Duration | Short speech under 5 s, medium passages, long passages, 30 minute repeated session | Queue order, memory growth, missed audio and cancellation matter as well as average speed. |

The initial 50 trials per target cannot establish a 99.9% reliability claim. Even approximately 3,000 independent zero failure trials only bound a failure probability near 0.1% at one sided 95% confidence under strong sampling assumptions. Real users and repeated sessions are correlated; report uncertainty and coverage rather than using this calculation as a certification shortcut.

### 7.4 Metrics and proposed decision thresholds

Freeze these proposals in the evaluation spec before final trials. They are deliberately separate from observed RC3 results.

| Metric | Definition | Proposed decision rule |
| --- | --- | --- |
| Primary user outcome | Time from stop action to text the user accepts as correct, including manual repairs and recovery | Aim for at least 20% lower median time than Wispr on the declared developer task set. Report a speaker clustered paired confidence interval; its 95% upper bound for the time ratio should be below 1 before claiming a win. |
| Critical factual errors | Missing, changed or invented annotated numbers, dates, negations and identifiers, with human review of intended corrections | Investigate every severe failure. No introduced severe semantic regression may remain unresolved. For a comparative claim, both point estimate and uncertainty must meet a preregistered noninferiority margin; proposed maximum is 0.5 percentage points worse. Do not claim zero risk. |
| Recognition | Raw WER and CER against the same spoken references, per language and group | Report wins and losses independently. A claim of better accuracy needs a measured reduction with uncertainty supporting it. |
| Visible delivery | Stop action to settled new text in the correct document | Reference goal for base on short speech: p50 about 1.2 s and p95 below 1.5 s. Show failures, cold cases and each hardware/model combination separately. |
| First attempt insertion | Verified correct target deliveries divided by intended normal condition trials | Proposed initial release target at least 99% observed per supported target on the declared matrix, with interval and denominator. This is not a 99.9% population claim. |
| Safety | Wrong target input, duplicates from automatic retry, clipboard loss, unauthorized external mutation | Any observed case blocks the affected release path until fixed and retested. Fault injection should exercise safe refusal and explicit recovery. |
| Setup | Fresh user reaches verified first dictation without maintainer intervention | Proposed pilot target at least 90% of participants within 5 minutes with bundled models, with failures counted. Small pilot results remain descriptive. |
| Companion value | Preference and distraction after real use, with companion available or hidden | Optional and independently measured. No preference claim from screenshots or developer enthusiasm. |

For time to accepted text, use a separate counterbalanced user task study so correction effort is real, not inferred from WER. Record active correction time, completion time and failures. Fix a timeout before running; report incomplete tasks as failures and censored observations, not fast successes. Publish success conditioned timing alongside all attempt completion rates. A faster median cannot override materially lower completion.

Cluster uncertainty by participant and account for repeated utterances. Define the primary language/task claim before seeing results. Per language claims need their own evidence; an aggregate dominated by English cannot certify Tamil. For multiple advertised wins, use a declared multiple comparison policy or treat additional results as exploratory. Do not select a favorable subset after the run.

Performance budgets beyond visible delivery should be declared before testing: cold readiness, loaded memory, idle CPU and long session growth. Suggested starting reference limits are base loaded process tree RSS below 800 MiB, small below 1.2 GiB, idle CPU below 1% of total machine capacity over 60 seconds, and no sustained post warmup memory growth beyond the greater of 32 MiB or 10% over 30 minutes. These are proposals requiring hardware validation. Measure peak and sampled values separately, and compare equal runtime states. Do not compare FlowPilot before model load with Wispr during active work.

### 7.5 Evidence format

Each run should identify: protocol version, source/executable/model hashes, corpus version and full fixture SHA-256, anonymized speaker, language/group, product settings, target/version, device route, machine, warm/cold state, monotonic timestamps and clock resolution, delivery outcome, recovery, errors, CPU/memory sampling method, and failure reason. No missing metric becomes zero.

Retain raw recordings and detailed text only in explicitly consented private storage with deletion terms. Commit sanitized aggregates, reproducible analysis commands, reference eligibility, and hashes where permitted. The benchmark runner should return an incomplete status when required records or consent are missing. Independently recompute report totals from raw records; include rejected attempts with reasons.

## 8. Improve what the measurements reveal

Existing `CorrectionIntentResolver`, `ProfileResolver`, vocabulary aliases, snippets, prompt budgets, local model lifecycle, scratchpad transactions, and recovery are starting points. Do not label them missing because an older document predates them.

Classify each failure before choosing a fix: capture/clipping, wrong microphone, recognition, script selection, vocabulary bias, intended correction, unwanted formatting, target focus, delivery, or user confusion. Change one layer at a time where practical. Keep negative cases, such as ordinary use of "actually", nearby nonmatching words, repeated names, changed document selections, and cancellation.

Try base and small on the development corpus; larger is not automatically better for the experience. Preserve distinct speed and quality profiles if one model cannot meet both goals. Model changes should honor the existing [promotion rule](../evaluation/REAL_VOICE_CORPUS_SCHEMA.md), including its short dictation latency gate. Do not silently relax that rule after a slow result.

Optional local language models remain explicit rewriting tools, not the default dictation dependency or general agents. Require local backend verification, bounded request ownership, cancellation, factual checks, and a preview or safe unchanged fallback. The presence of a loopback URL alone does not establish that a third party backend never forwards content.

If the error analysis shows that missing context is a major cause, feature 30 can evaluate an explicit opt in for a small amount of surrounding text in a supported field. Exclude password and sensitive or unsupported controls, impose a total 500 ms acquisition budget off the UI thread, discard data after use, and continue normal dictation when unavailable. Context is data, never an instruction to execute actions. Compare benefit on held out tasks before enabling it by default. Screenshot collection, general workspace filename scanning and passive clipboard watching are not part of this proposal.

## 9. Whole app acceptance, not just a dashboard screenshot

Create a control inventory with page, control, enabled/disabled states, action, backend effect, persistence, cancellation, failure behavior, and evidence. Every visible button, menu, shortcut, dropdown, slider, link, and import/export route should have a meaningful outcome or a clear unavailable state.

| Surface | Required journeys |
| --- | --- |
| Setup | No mic, denied mic, missing/corrupt model, chosen language, practice dictation, recovery, back/next/cancel, rerun setup, offline first launch |
| Home and navigation | Truthful readiness and last status, all destinations, history disabled/empty, copy/paste recovery, return from a failed view |
| Settings and hotkeys | F9, hold/toggle, conflict detection, reserved shortcuts, cancel, restoration after restart, immediate changes, no accidental wheel changes |
| Dictionary and snippets | Search/add/edit/delete, duplicate and overlapping aliases, language/profile scope, literal symbols, import/export limits, malformed files, deletion tombstones |
| Scratchpad and transforms | Save/open/export, exact selection and Unicode offsets, preview/apply/undo, revision changes, worker cancel, hide/close, unavailable local LLM; external Replace/Revert disabled |
| History and insights | History off/on, existing entries, retention, delete, playback stop, honest empty statistics, no invented readiness or usage |
| Meetings | Source selection, start/pause/resume/stop, disconnect, long recording, correct timestamp ranges, grounded summaries, translation mode, export/delete and separate storage |
| Studio and creator | Preview versus Apply/Cancel, all states, palettes, emoji, PNG/GIF/sprite imports, frame mappings, reduced motion, export/reimport, app rules and restoring Hidden |
| Tray and recovery | All truthful statuses, Show/Hide, Paste Last/Copy Last, failed target, quit, duplicate launch and no orphan audio listeners |

Test light and dark themes, keyboard navigation and accessible names, Windows Narrator on essential controls, text scaling, and 100/125/150/200% display scaling where supported. Cover the declared minimum usable resolution, scroll reachability, multi monitor movement and unplug. Scrolling a page over a setting should not change its value unless the user deliberately interacts with that control; keyboard selection and an open dropdown still need to work.

The passive HUD must preserve editor focus. Intentionally opened Studio, settings and scratchpad must accept keyboard input. These are different focus contracts. Keep navigation reachable when a view errors. Do not trim padding or redesign unrelated surfaces without a measured defect or an agreed design change.

## 10. Companion quality and originality

Keep a small coherent set of original characters and one minimal presentation. Verify idle, listening, processing, confirmed delivery, unverified delivery and recoverable failure at actual desktop size. Success animation requires verified success. Reduced motion and Hidden stop unnecessary animation.

Test a simple adopt/customize/save journey with new users, then a create/import/export journey. Evaluate readability, distraction and desire to keep using the character separately from dictation quality. Do not add artificial retention claims or assume more presets means a better product.

Verify import file size, decoded dimensions, frame count, malformed content, archive traversal, decompression growth and total in-memory bounds before accepting a pack. Shared packs contain only intended assets and metadata, without profile paths, dictionary contents, transcripts or executable hooks. Keep creator, preview and HUD mappings consistent for 1 through 12 frames.

Maintain an asset provenance list with creator, source, license, modifications and required notices. Use original or appropriately licensed assets; do not bundle extracted competitor code, copied franchise characters, or third party credentials. A filename scan is useful but does not replace inspecting the actual bundle and notices.

## 11. Privacy, data, security and lifecycle

Use non-sensitive canaries in controlled tests. Verify the ordinary dictation path offline and inspect the files and network paths actually exercised. No transcript or audio should be written by the history path when history is disabled. Test success, failure, cancellation, retry and shutdown. Distinguish application writes from OS paging and crash dump behavior; never promise forensic erasure from a setting toggle.

| Boundary | Evidence needed |
| --- | --- |
| History and recovery | Default no history, explicit enable, existing data not silently erased, deletion/retention, recovery buffer lifecycle, retry does not create hidden WAV files |
| Meeting and scratchpad data | Separate storage disclosure, local save/delete/export, no misleading claim that dictation history off disables all persistence |
| Diagnostics | Synthetic sensitive canaries absent from ordinary logs, telemetry and exception messages; exports reviewed before sharing |
| Local API | Off unless enabled, loopback only, authentication, WebSocket origins, body/concurrency limits, multipart temp file cleanup, no unnecessary desktop privileges |
| Local LLM | Allowed local endpoints, no proxy or redirect bypass, unavailable backend, deadlines, cancellation, bounded outstanding work, independent backend egress boundary |
| Clipboard and input | Supported formats documented; text plus rich content cases tested; newer user copy preserved; no mutation after uncertain focus; no credentials read |
| Dependencies and assets | Inventory from final bundle, model/art notices, vulnerable dependency review, no copied competitor artifacts or secrets |
| Lifecycle | Single instance, model/mic errors, sleep/resume, clean quit, pending workers, device listeners and visibility sampler cleanup |

Document precisely whether network evidence is instrumented sockets, process monitoring or a whole system capture. Offline flags and a self-test alone do not establish zero bytes across every possible feature. No HIPAA, GDPR, ITAR or other certification claim follows solely from local processing.

Test fresh setup and copies of at least two supported real upgrade profiles, one history disabled and one enabled with existing records. Preserve microphone choice, hotkeys, language/model, dictionary, snippets, companion/rules and privacy choices. Include migration write failure and rollback behavior. Do not test by modifying the user's only real profile. Document which older binaries cannot read newer settings and how to restore a backup safely.

## 12. Pilot and release decision

Start with 8 to 12 consenting Windows users over about five working days as a discovery pilot, not a population reliability study. Use the exact archive, clear unsigned status if applicable, local data disclosures, tasks and recovery instructions. Record participant dropouts and unsuccessful setup; they are product outcomes.

Ask whether users complete their ordinary developer writing more easily, how often they correct or recover text, where they stop using the product, and whether the companion helps or distracts. Collect only explicitly agreed diagnostics. Measure preference for dictation and preference for the companion separately. A small preference vote is not proof of broad market superiority.

Before public release, close all blocking product and trust rows, record remaining limitations, and complete the [release evidence template](../release/RELEASE_EVIDENCE_TEMPLATE.md). Recommend a verified publisher signature for broad distribution; an unsigned pilot must remain clearly disclosed. Signing does not guarantee SmartScreen reputation and changes the tested bytes.

Use a new candidate version when application bytes change. Do not overwrite RC3, move an existing release tag, or reuse its test record for a different build. The complete bundle size includes models and libraries. Consider a clearly disclosed base package plus an optional offline quality model pack only if packaging work preserves first launch offline behavior; do not silently remove required weights to advertise a smaller installer.

Build from a fixed source identity before running packaged checks. Point tests at the exact candidate. After signing or rebuilding, recheck affected behavior, smoke, offline model loading, archive CRC, embedded executable match, hashes and notices. Hosted CI must pass on the intended source commit, with headless skips stated separately. Retain one current manifest and explicitly historical prior records.

Typical existing commands, run only in an appropriate isolated test environment:

```powershell
python -X utf8 tests/run_all_tests.py --require-all
npm test
python -X utf8 desktop_app.py --self-test
Get-FileHash -Algorithm SHA256 -LiteralPath .\dist\FlowPilot\FlowPilot.exe
Get-AuthenticodeSignature -LiteralPath .\dist\FlowPilot\FlowPilot.exe
```

The source self-test does not validate a package. Run the corresponding packaged `FlowPilot.exe --self-test` against the final artifact with an isolated empty cache. Stage test environment variables before importing engine modules. The suite count is whatever the reviewed runner defines; never force it back to 54 after adding legitimate suites.

## 13. Concrete work packages for Gemini

Keep changes modular and make each one independently reviewable. Suggested PR boundaries are recommendations, not permission to publish or change unrelated files.

| Package | Scope and output | Required review evidence |
| --- | --- | --- |
| P0 | Reconcile current scope and evidence, complete remaining live acceptance rows | Checklist with exact artifact and actual outcomes, no forced passes |
| P1 | Persistent input identity and migration | Deterministic identity tests plus real reconnect/restart and recording continuity |
| P2 | Benchmark observer, record schema and analysis | New text delta timing, accuracy independent of delivery, calibrated clock, failure accounting |
| P3 | Consented corpus and baseline reports | Correct references, speaker splits, missing data handling, raw-to-summary reproducibility |
| P4 | Highest impact recognition/formatting/delivery fixes | Failure examples, focused regressions, held out improvement, no semantic or focus regression |
| P5 | Whole app controls, accessibility and companion acceptance | Control matrix, real backend effects, scaling/wheel behavior, privacy and asset checks |
| P6 | Upgrade, optional API, storage and final packaging hardening | Data and network boundaries, fresh/upgrade profiles, dependency/model/art inventory |
| P7 | Pilot, final comparison and release decision | Frozen protocol results, failed categories, uncertainty, exact final candidate and claims review |

Reuse `benchmarks/run_real_voice_eval.py`, `benchmarks/runtime_metrics.py`, `engine/evaluation_metrics.py`, the corpus schema, and existing test harnesses. Do not create a second competing benchmark system. Do not rewrite the whole app, add a web renderer, add cloud inference, train a model from scratch, or expand to mobile to avoid the evidence gaps.

If physical desktop access, a target application, native speakers, signing credentials, or a machine is unavailable, complete independent work and record the specific unmet dependency. Do not convert it into a pass or request repeated authorization for already authorized read only work. Live input probes need an idle desktop and must never type into an unrelated user window.

## 14. Evidence ledger and honest signoff

Maintain one row per acceptance criterion with: scope ID, criterion ID, owner, source/build identity, environment, method, result, raw evidence link/hash, limitation, reviewer and date. Allowed results are verified, failed, blocked, not run, or not applicable with reason. "Implemented" alone is not a verification result.

Before closing a stage, independently recompute counts and reported metrics, check links and hashes, and review at least one unsuccessful path. Retain historical failures and show which change fixed them. Never remove a skip guard, force a success variable, substitute a safe abort for delivery, or rename a timing endpoint to make a gate green.

The current planning review identified documentation drift: old RC2 references in release instructions, companion scope rows not reflecting the completed RC3 subset, a source-only description of packaged transform repairs, and root context that still describes fullscreen verification as wholly pending. Scope wording is reconciled with this handoff; remaining context and release wording should be updated narrowly by their owners without rewriting historical evidence.

At final review produce:

1. A complete scope status table with later items explicitly deferred and all required acceptance rows linked.
2. A reproducible comparison report including wins, losses and inconclusive results.
3. A pilot report including installation failures, recovery use and retention of user settings.
4. A release record tied to final bytes, publisher status, exact CI and physical evidence.
5. A public claim draft limited to the supported result.

Acceptable claim template, only after measurements support it:

> On [dated Windows developer task set], FlowPilot [version/model] reduced median time to correct, usable text by [measured percentage, interval] compared with Wispr Flow [version/settings], across [speakers/tasks/machines]. [State factual error and delivery outcomes.] FlowPilot processed the tested dictation locally. Results outside these conditions are not established.

If the result does not meet the proposed competitive gate, release readiness can still be assessed on its own merits, but no superiority claim follows. A truthful result and a clear next fix are more valuable than another unsupported declaration of completion.

## 15. Immediate next action

Start P0 using the unchanged RC3 artifact: reconcile the acceptance ledger and complete the missing spec 0001 live rows when the desktop is idle. In parallel with evidence preparation, design feature 28 and the observation contract for feature 29. The first product code change should address persistent input selection; the next measurement change should observe actual delivered text. Recruit the required speakers before scheduling the final comparison.

This is the complete plan for the defined Windows release and competitive evaluation. It is not a statement that the plan has been executed, that all software defects are eliminated, or that FlowPilot is already superior in every situation.

## 16. Code integration and review contract

The following paths and symbols were inspected at `6555e3d`. Recheck them at the implementation commit. If they have moved, update this map from source rather than guessing a similarly named file. Copying every source line into a planning document would create a second, stale codebase; the source files are authoritative for implementation, and these contracts identify the changes and review boundaries.

### 16.1 Existing runtime call paths

```text
Dictation control / hotkey
  -> FlowOrchestrator.start_dictation()
  -> AudioRecorder.start_recording()
  -> FlowOrchestrator.stop_dictation_and_process()
  -> AudioRecorder.stop_recording()
  -> STTEngine.transcribe()
  -> ContextProcessor.process()
  -> TextInjector.inject_with_status()
  -> InjectionResult + injection_completion_timing()
  -> FlowPilotApp StateBridge -> UI status

Settings / setup
  -> updated config -> FlowOrchestrator.update_config()
  -> recorder.set_device(..., defer_if_recording=True)

Scratchpad spoken editing (separate flow)
  -> ScratchpadView command recorder -> VoiceCommandWorker
  -> STTEngine + VoiceEditor transaction planning
  -> preview -> guarded apply / undo / cancel

Benchmark observation (new work)
  -> owned target baseline and session -> stop action timestamp
  -> independent new document content observation
  -> per trial result -> aggregate report
```

This is an ownership map, not a claim that every arrow is synchronous or executes on the same thread. Preserve current worker and session ownership when making changes.

### 16.2 P1 exact device integration points

| Existing code | Required inspection/change |
| --- | --- |
| [engine/config.py](../../engine/config.py): `get_config_file`, `load_config`, `save_config` | Version and migrate the persisted selection contract, preserve atomic saves and old user choices. `audio_device_index` and legacy `mic_device` currently exist as consumed settings; do not silently reinterpret either as a persistent ID. |
| [engine/audio_recorder.py](../../engine/audio_recorder.py): `AudioRecorder.__init__`, `_warmup_stream_locked`, `warmup_stream`, `set_device`, `stop_recording`, `close` | Accept the resolved current runtime route. Preserve `RLock`, pending switch flag separate from `None`, pre-roll, captured frames, safe deferred switching, and cleanup. Do not serialize the stream or create an extra listener to preserve it across focus changes. |
| [engine/orchestrator.py](../../engine/orchestrator.py): `FlowOrchestrator.__init__`, `update_config` | Resolve startup selection and settings updates through one resolver. Track requested versus actually active route during a deferred change; do not report the new microphone active before switching succeeds. Handle persistence/stream failures coherently. |
| [ui/settings_dialog.py](../../ui/settings_dialog.py): `_build_general_tab`, `_save_settings` | Current combo data is an integer and names are deduplicated. Show enough identity to distinguish devices/APIs. Save the selection contract, not a transient list position. |
| [ui/setup_wizard.py](../../ui/setup_wizard.py): `_populate_mics`, `_start_mic_test`, `_finish_setup` | Preview/test and final saved selection must resolve the same device. A missing selection must not silently become the first entry. |
| [ui/scratchpad_view.py](../../ui/scratchpad_view.py): `_get_audio_recorder`, `_start_command_recording`, `_cancel_command_recording` | Command capture currently reads the numeric setting too. Use the same resolver. Preserve its deliberately separate recording ownership and close/hide cancellation behavior. |
| [desktop_app.py](../../desktop_app.py): `_on_save_settings`, `show_setup_wizard` | Verify wiring and actual readiness/error feedback. Avoid a second independent device choice in the UI layer. |

A new small resolver module may be appropriate, for example `engine/audio_devices.py`; that file does not exist at this baseline and the name is only proposed. The spec should define an explicit system default mode versus a specific persistent endpoint, API disambiguation, migration, and a result such as resolved/default/missing/ambiguous/unavailable. A saved name alone or an index renamed to `device_id` does not solve identity.

Concrete P1 regression: microphone A is index 4 at save time. At restart A is index 12 and microphone B is index 4. The selection must still resolve to A or clearly fail if identity is unavailable; selecting B is a failure. Also test duplicate names across endpoints/APIs, unavailable A, explicitly choosing default, device removal while recording, deferred switching, return to default, failure opening the new stream, and config write failure. Define policy for each failure in the spec instead of silently inventing a fallback.

### 16.3 P2 exact timing integration points

| Existing code | Contract to preserve or extend |
| --- | --- |
| [engine/orchestrator.py](../../engine/orchestrator.py): `injection_completion_timing`, `stop_dictation_and_process`, `last_pipeline_timing` | Existing stop and acoustic endpoint times end at the injection result. Preserve `stop_action_to_visible_text_ms: None` and `visible_delivery_status: not_measured` when there is no independent observer. |
| [engine/text_injector.py](../../engine/text_injector.py): `InjectionResult`, `inject_with_status`, `_resolve_verified_foreground`, `read_window_buffer`, `_verify_new_text_injected` | Inspect its focus and document verification behavior. A boolean or returned status does not provide the timestamp of first/settled appearance. Do not weaken focus or clipboard safeguards to get a sample. |
| [benchmarks/run_real_voice_eval.py](../../benchmarks/run_real_voice_eval.py): `run_evaluation` | Reuse corpus/model/environment reporting. This evaluates processing and is not itself a live delivery observer. Keep that mode usable without a desktop. |
| [benchmarks/runtime_metrics.py](../../benchmarks/runtime_metrics.py): `percentile`, `summarize_processing_trials`, `collect_runtime_environment` | Keep processing and observed document summaries separate. Missing observations remain unknown; failures and denominators remain visible. |
| [engine/evaluation_metrics.py](../../engine/evaluation_metrics.py), [engine/real_voice_corpus.py](../../engine/real_voice_corpus.py) | Reuse references, language normalization, corpus integrity and fact scoring. Delivery timing must not depend on matching the correct reference output. |
| [tests/notepad_harness.py](../../tests/notepad_harness.py): `open_test_notepad`, `is_interactive_desktop`, `focus_notepad_document`, `paste_and_verify_notepad`, `cleanup_test_fixture` | Reuse owned fixture/focus/cleanup concepts. Its retry helper is not the first attempt clock; classify any recovery separately. |
| [engine/voice_editor.py](../../engine/voice_editor.py): `VoiceEditor.plan_edit`, `apply_transaction` | Leave out of normal dictation timing instrumentation. It is relevant only to a separate spoken editing benchmark with its own endpoints. |

Put new observation logic in a focused benchmark module, for example proposed `benchmarks/delivery_observer.py`, instead of turning `voice_editor.py` into a general timer or adding editor surveillance to the product. Reuse the existing evaluator/report utilities rather than duplicating them.

The observation record should carry a unique trial/session, target identity, baseline revision, stop event, first changed content time, settled content time, observation method and resolution, outcome, and missing-data reason. Use one monotonic clock or explicitly align clocks. Target document readback measures document availability, not the exact pixel paint time; name that boundary in the report. Validate the settlement policy against incremental output and pauses before using it for a comparison.

Required P2 fixtures: identical text already present before dictation; wrong transcription newly inserted; two identical successive utterances; partial/incremental output; delayed paste; no paste; unreadable target; wrong target; cancellation; duplicate output; recovery after a failed first attempt; observer timeout. Wrong transcription can be observed delivery with poor accuracy. Preexisting matching text is not new delivery. An unobserved result cannot have a zero latency.

### 16.4 Product ownership and existing verification map

Use these as starting suites, then add meaningful tests for changed behavior. Their existence does not prove the new work has passed. If a new test module is added, wire its executable entry into `tests/run_all_tests.py` so a reported full gate actually includes it.

| Concern | Existing source | Existing suites to inspect |
| --- | --- | --- |
| Device selection and capture | `engine/audio_recorder.py`, `engine/orchestrator.py`, settings/setup/scratchpad above | `tests/test_user_facing_fixes.py`, `tests/test_audio.py`, `tests/test_orchestrator_state_machine.py` |
| Session and timing contracts | `engine/session.py`, `engine/orchestrator.py`, `benchmarks/runtime_metrics.py` | `tests/test_session_lifecycle.py`, `tests/test_evaluation_metrics.py` |
| Models, VAD, prompts and languages | `engine/stt_engine.py`, `engine/silero_vad.py`, `engine/prompt_budget.py`, `engine/language_registry.py` | `tests/test_stt.py`, `tests/test_model_lifecycle.py`, `tests/test_silero_vad_resolution.py`, `tests/test_personalization_pr3.py`, `tests/test_language_registry.py` |
| Formatting and deliberate corrections | `engine/writing_intelligence.py`, `engine/context_processor.py`, `engine/correction_intent.py` | `tests/test_writing_intelligence.py`, `tests/test_correction_intent.py`, `tests/test_factguard_adversarial.py`, `tests/test_factguard_v2.py`, `tests/test_application_profiles.py` |
| Vocabulary and snippets | `engine/personalization.py`, `ui/dictionary_view.py`, `ui/snippets_view.py` | `tests/test_personalization.py`, `tests/test_personalization_pr3.py`, `tests/test_personalization_snippets.py`, `tests/test_user_facing_fixes.py` |
| Target delivery and recovery | `engine/text_injector.py`, `engine/window_inspector.py` | `tests/test_text_injector.py`, `tests/test_target_verification_modern_apps.py`, `tests/test_notepad_dictation_e2e.py`, `tests/test_cross_app_injection.py`, `tests/test_final_specification_e2e.py` |
| Voice editing and local rewriting | `engine/voice_editor.py`, `engine/transforms_engine.py`, `engine/local_llm.py`, `ui/scratchpad_view.py`, `ui/transforms_view.py` | `tests/test_voice_editor_pr4.py`, `tests/test_voice_command_and_llm.py`, `tests/test_honest_transforms.py`, `tests/test_transforms_and_history.py` |
| Setup, navigation, scrolling and hotkeys | `desktop_app.py`, `ui/flowpilot_dashboard.py`, `ui/workspace_home.py`, `ui/workspace_style.py`, settings/setup, `engine/hotkey_service.py` | `tests/test_workspace_refresh.py`, `tests/test_flowpilot_dashboard.py`, `tests/test_settings_dialog.py`, `tests/test_hotkey.py`, `tests/test_win32_hotkey.py`, `tests/test_desktop_app.py` |
| Companion policy and media | `engine/companion_visibility.py`, `engine/media_presence.py`, `engine/companion_store.py`, `ui/companion_visibility_controller.py`, `ui/tray_manager.py` | `tests/test_companion_visibility.py`, `tests/test_companion_studio.py`, plus the separate live checklist |
| Rendering and creator | `engine/companion_assets.py`, `ui/companion_renderer.py`, `ui/companion_preview.py`, `ui/floating_hud.py`, `ui/pet_sprites.py`, `ui/pixel_creator.py` | `tests/test_kiki_companion.py`, `tests/test_sondercat_companion.py`, `tests/test_pixel_companions_and_creator.py` |
| Local preferences | `engine/preference_learning.py`, `engine/personalization.py`, `ui/companion_studio.py` | `tests/test_companion_studio.py`, `tests/test_companion_visibility.py`, personalization suites |
| History and insights | `engine/history_vault.py`, `engine/insights_engine.py`, `ui/history_view.py`, `ui/insights_view.py`, `engine/orchestrator.py` | `tests/test_transforms_and_history.py`, `tests/test_insights_engine.py`, `tests/test_review_integration.py` |
| Meetings and translation | `engine/meeting_notetaker.py`, `engine/meeting_deliberation.py`, `ui/notetaker_view.py` | `tests/test_meeting_notetaker.py`, `tests/test_meeting_notetaker_v2.py`, `tests/test_meeting_deliberation.py`, `tests/test_multilingual_workstation.py` |
| Privacy, API and packaging | `engine/server.py`, `engine/config.py`, `engine/single_instance.py`, `flowpilot.spec`, `.github/workflows/ci.yml` | `tests/test_network_egress.py`, `tests/test_api_and_websocket.py`, `tests/test_fullstack_node_client.mjs`, `tests/test_release_integrity_fixes.py`, `tests/test_standalone_binary_smoke.py` |

Preserve these existing contract tests specifically: `test_injection_timing_does_not_claim_visible_delivery` in `test_session_lifecycle.py`, `test_runtime_summary_keeps_unmeasured_delivery_unknown` in `test_evaluation_metrics.py`, and the real warmup/deferred/default/frame preservation tests in `test_user_facing_fixes.py`. Do not update their expected outcomes to bless a regression.

### 16.5 Approved local learning, scope feature 31

The existing `PreferenceLearningEngine` records deliberate settings choices when enabled, proposes rules after at least three distinct calendar days and 80% consensus, and supports acceptance, dismissal, forgetting and tombstones. It is not a general Hermes agent, model training, or automatic understanding of all user edits. `PersonalizationEngine` already stores approved terms, aliases and snippets, with shared listeners and scopes.

The later enhancement should provide an explicit Teach or Remember correction action. Show the exact source phrase, replacement, language and optional app/profile scope before saving. Remember only the approved rule, not a surrounding transcript or passive editor history. Apply it through existing personalization and context processing, with clear precedence and a way to inspect, edit, undo, delete and disable it.

Use `get_shared_personalization()` rather than creating a second store. Inspect `PersonalizationEngine.add_term`, `add_alias`, `get_scoped_entries`, `apply_dictionary`, and deletion behavior. Reuse `PreferenceLearningEngine` for its existing settings proposal domain; do not overload it with transcript retention. Any new correction proposal schema or UI belongs in a feature 31 spec before implementation.

Acceptance cases include wrong proposed correction rejected, overlapping aliases, language/profile boundaries, immediate application after approval, disabled learning, repeated clicks, deletion across restart and import, and semantic facts that should not be changed by a broad rule. A forgotten rule must not reappear automatically. No external agent process, cloud service, autonomous tool use or passive keystroke/clipboard collection is needed. Priority remains after the core device, delivery and real speech work.

### 16.6 What Gemini should return for review

Start with a short source inspection record, not a menu asking the owner to locate modules. For every submitted work package, provide:

1. Base commit, current branch, worktree status, changed files, and the applicable AGENTS/spec sections read.
2. The corrected problem statement, actual call path, proposed or implemented data contract, and why the change addresses that failure.
3. Focused test commands and raw results, including failures, skips, exclusions, timing boundaries, and whether hardware was mocked.
4. For physical checks, the exact executable hash, isolated profile, target/device identity, observation and failure/recovery classification.
5. For a build, source provenance, full bundle/archive identity, smoke and offline results, signing status, and distinction from historical RC3.
6. A criterion-by-criterion summary with evidence links and remaining limitations. No claim that a short report or suite count completes the entire product.

Codex review should inspect the actual diff and evidence, check the boundaries above, and independently reproduce the affected meaningful checks where the environment allows. A completion message alone is not review evidence. If only a proposal was supplied, assess it as a proposal; do not claim its code is fixed or its runtime is verified.
