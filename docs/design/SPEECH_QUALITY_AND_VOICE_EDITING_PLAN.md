# FlowPilot: multilingual speech quality and safe voice editing

Status: proposed implementation plan, 2026-10-21. Inspected source: `0850e4d` (release code commit `a302b80`). This document extends [the competitive product specification](FLOWPILOT_COMPETITIVE_PRODUCT_SPEC.md); it does not certify a release or change the offline architecture directive.

## Decision in plain words

Make FlowPilot better at hearing the user, remembering explicitly taught spellings, and editing only what the user asks to edit. Start with English, Hindi, Tamil and Malayalam. Test English mixed into each of the other three languages as separate cases. Keep ordinary dictation fast; activate richer editing deliberately. Do not build a general autonomous agent or train a speech model from scratch.

The model is already pretrained. A personal dictionary supplies hints and preferred spellings; it does not retrain the acoustic model. Fine-tuning needs paired speech recordings and correct transcripts, not a bigger word list. The official [Whisper fine-tuning walkthrough](https://huggingface.co/blog/fine-tune-whisper) illustrates that distinction. First measure whether capture, model size, language selection, vocabulary or formatting caused the error.

Product hypothesis: multilingual Windows developers will keep using FlowPilot if they spend less time correcting names, code and mixed-language sentences, with no speech sent to a service. Original companions can help people want the product; they cannot compensate for incorrect words. Validate those two benefits separately.

## What is actually present, and what is missing

These are source findings and small, hardware-free diagnostics, not a new acoustic benchmark.

| Area | Observed implementation | Consequence / next action |
| --- | --- | --- |
| Speech recognition | `engine/stt_engine.py` uses faster-whisper, CPU INT8 and offline-only weights; the default is multilingual `base`. | Compare alternatives on the actual workstation before changing the default. |
| Language picker | `LanguageRegistry.get_language()` returns entries for `en` and `hi`, but `None` for `ta` and `ml`. | Add Tamil and Malayalam across picker, setup, session configuration and script tests. Backend language coverage is not product-quality proof. |
| Changing the model | `FlowOrchestrator.update_config()` replaces `stt.config`, but `_get_local_model()` returns the existing cached object. | A diagnostic requested `small` after loading mocked `base`: loader calls stayed at one and the same object was returned. Fix identity/lifecycle before trusting live model switching. |
| Vocabulary | `build_bias_prompt()` includes all personal terms via `get_terms_list()` and the registry joins them without a tokenizer budget. | Rank and bound hints. The separate `build_whisper_prompt(max_terms=50)` helper does not bound this active path. |
| Understanding instructions | Selected-text transforms and an optional `LocalLLMProvider` already exist. | Reuse them selectively; no need for an agent framework. Add explicit edit intent and transactional application. |
| Unsupported instructions | With the local LLM mocked unavailable, asking to replace Friday with Monday shortened the sentence but left Friday unchanged; FactGuard returned true. | Unsupported editing must return `unsupported` and leave text unchanged, not silently run an unrelated transformation. |
| External text editing | Selection capture simulates Ctrl+C; replacement and revert use the injector without a document revision/range transaction. | Audit clipboard ownership, selection identity, apply status and undo before exposing spoken destructive edits. |
| Existing accuracy evidence | The tracked VB-Cable JSON contains 15 synthetic SAPI trials. Raw and formatted WER use different references; timing excludes insertion. | Keep it as synthetic regression evidence. It does not establish real-speaker, four-language or paired Wispr accuracy. |

Inspected workstation: Intel Core i5-12500H, 12 physical / 16 logical cores, about 15.7 GiB RAM. Installed packages inspected: faster-whisper 1.1.0, CTranslate2 4.8.1. Only `base` was found in the repository's model directory; other caches were not exhaustively inventoried. Hardware availability is not a latency guarantee.

### Important safety distinction

FactGuard compares candidate text with the recognized transcript. It cannot establish that the transcript correctly heard the original audio. Nor does passing its current checks mean an editing instruction was followed. Measure acoustic facts, formatting changes and instruction fulfillment independently.

## What the competitor research supports

- Wispr documents 100+ languages, but its current help page says language identification is per dictation rather than per word. Hinglish is an explicit script/output choice. Do not equate a language count with reliable mixed-language speech. [Wispr language behavior](https://docs.wisprflow.ai/articles/3191899797)
- Wispr describes language-specific ASR selection and formatter training. That is vendor-reported architecture, not our independent inspection or proof that FlowPilot should run several models for every utterance. [Wispr multilingual research](https://wisprflow.ai/research/supporting-languages)
- Wispr has a separately activated desktop Command Mode for editing existing text. A bounded local equivalent fits FlowPilot's writing-assistance scope; web searches and autonomous actions do not. [Wispr Command Mode](https://docs.wisprflow.ai/articles/4816967992-how-to-use-command-mode)
- Aqua Voice explicitly advertises a customizable desktop pet. I did not find official evidence that Wispr ships Naruto, Harry Potter or Star Wars character packs. [Aqua Pet](https://aquavoice.com/pet), [Wispr features](https://wisprflow.ai/features)

## Model selection: candidates, not promises

| Candidate | Place in this workflow | Qualification |
| --- | --- | --- |
| Multilingual Whisper `base` INT8 | Existing baseline and lightweight option. | Keep until another configuration wins on measured quality and responsiveness. |
| Multilingual Whisper `small` INT8 | First challenger for the four selected languages. | Uses the existing runtime; measure CPU latency, loaded memory and accuracy. Larger is not automatically better for this user's workflow. |
| Multilingual Whisper `medium` INT8 | Optional quality experiment if `small` remains inaccurate. | Do not silently install or promote it; package size, memory and short-utterance latency need evidence. |
| Distil-Whisper `distil-small.en` | Possible later English-only experiment. | English-only, so not a replacement for the four-language baseline. [Model card](https://huggingface.co/distil-whisper/distil-small.en) |
| Moonshine streaming | Later low-latency English experiment. | Different runtime integration. Its current published language table does not cover Hindi, Tamil or Malayalam; inspect each checkpoint's license. [Available models](https://moonshine-voice.readthedocs.io/en/latest/models/available-models/) |
| AI4Bharat IndicConformer | Specialist candidate if Indic-language quality is inadequate. | Its MIT-licensed 600M multilingual card lists Hindi, Tamil and Malayalam and an ONNX implementation. Access is gated; CPU performance, code-token handling and packaging remain unmeasured here. [Model card](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual) |
| Bodhan / AI4Bharat Indic-Transcribe | Research candidate, not a drop-in upgrade. | The upstream IndicConformer card now recommends it. Its card describes native-script output, including English words within Indic speech, and a custom license. Those are significant constraints for developer code identifiers; review exact terms and benchmark first. [Model card](https://huggingface.co/bodhan-ai/indic-transcribe-core) |

Use multilingual checkpoints, not `.en`, for Hindi/Tamil/Malayalam. Whisper `turbo` is not trained for speech-to-English translation, so it cannot silently replace a translation-capable model. Published GPU speed tables do not predict this laptop's CPU dictation latency. [Whisper models and translation guidance](https://github.com/openai/whisper#available-models-and-languages), [faster-whisper runtime](https://github.com/SYSTRAN/faster-whisper)

Do not run every candidate on every live utterance. Start with one selected ASR model and fixed settings. A specialist per-language route is justified only by reproducible improvement large enough to pay for added maintenance and model residency.

## Delivery sequence

### PR 1 — Make language and model settings truthful

Scope: `engine/language_registry.py`, `engine/stt_engine.py`, `engine/orchestrator.py`, their settings/setup consumers and focused tests.

- Add `ta` / Tamil / தமிழ் and `ml` / Malayalam / മലയാളം, with native-script output and explicit experimental quality labels until real-speaker validation. Do not translate speech to English unless requested.
- Capture language, translation mode, model identity and vocabulary version at session start. Settings changes affect the next session, never a session already recording or transcribing.
- Key model ownership by resolved asset identity and inference settings, not just whether `_local_model` is non-null. Serialize preload/reload; avoid two competing loads and changing a model during inference.
- Show requested versus active model and loading/failure state. Validate assets before committing a choice, keep the old working model on failure where memory permits, and provide an explicit recovery path otherwise.
- Check direct `FLOWPILOT_MODEL_DIR` overrides: a directory containing `base` weights must not be reported as a measured `small` run. Record revision/hash and effective settings in benchmark metadata.
- Preserve F9 and the user's other chosen shortcuts. Future edit-mode binding must pass conflict validation and must not silently restore old default bindings.

Acceptance: tests cover base-to-small, failed/missing assets, concurrent preload, update during dictation, restart persistence, Tamil/Malayalam selection, explicit translation and no runtime download. Begin with mocked loaders; repeat against separately provisioned local weights before claiming working acoustic model switching.

### PR 2 — Build the real-voice evaluation loop

Start small: 40 explicitly recorded utterances, ten per priority language, to debug routing and scoring. This is a development smoke set, not evidence for broad language support. Then build a held-out set with at least 50 utterances per language and several speakers per language. Add separate English-Hindi, English-Tamil and English-Malayalam mixed-sentence groups. Expand difficult groups after reviewing errors, without changing the locked test set to favor a candidate.

Keep development and final evaluation speakers/sessions and scripted sentences separate. Only consented, deliberately recorded evaluation audio may be stored. No passive microphone collection, clipboard watching or transcript harvesting; ordinary never-store mode remains unchanged. Put private corpus material in an explicitly chosen ignored folder, not public Git. Commit only authorized redistributable fixtures, aggregate results and a non-sensitive manifest.

Include normal speech, low volume, real accents, typing/fan noise, pauses, rapid bursts, silence, names, URLs, mixed-script developer tokens, CLI flags, dates, signed/decimal quantities, negation and self-corrections. Native speakers review the references. Distinguish clean audio with no added noise from controlled noisy trials: 0 dB SNR means equal signal/noise power, not clean speech.

Required measurements:

| Measurement | Definition |
| --- | --- |
| Raw recognition WER | All ASR candidates against the same spoken reference and versioned language-aware normalization. Report per language, speaker and condition. |
| Character accuracy | Unicode-aware CER alongside WER; retain combining marks and document normalization. Never strip Indic marks with an ASCII-oriented cleanup. |
| Formatted output quality | A separate score against an independently approved desired-writing reference. Never call its difference from raw-reference WER an ASR error reduction. |
| Critical facts and identifiers | Exact identifiers including punctuation/case; numbers with sign, decimal, unit and binding; dates and negation with scope/order/multiplicity. Set membership alone is insufficient. |
| Timing | Separately record model cold load, WAV-to-raw, formatting, speech-end-to-visible-text and recovery time. Report warm/cold, utterance-length buckets, p50/p95 and sample count. |
| Cost on device | Loaded-model and peak whole-process-tree memory, CPU demand, disk/model size, idle cost and thermal/long-session effects. |
| Usability | Human correction time per utterance, first-paste success, safe aborts, unverified outcomes and duplicate insertion. |

Use direct WAV inference to isolate model quality, then replay identical WAVs through VB-Cable to evaluate capture and full insertion. Resolve endpoints by identity/name/host API at run time, not stale device numbers. Log effective settings, source/build hash, fixture hashes and audio format. Only call it a head-to-head comparison when both products have outputs and timings for the same trials; competitor process memory alone is not a paired dictation result.

Run `base` versus `small` first, with the same language, beam, temperature, threads, VAD and vocabulary configuration. Use fresh model ownership per candidate. Test vocabulary changes separately. Do not download large weights without an explicit provisioning step. Count errors and missing runs, not just successful samples.

### PR 3 — Teach words without secretly training on the user

- Add a deliberate correction action: heard form, preferred spelling, optional aliases, language and optional app/profile scope. Preview the mapping and allow edit/delete; preserve deletion tombstones.
- Support several aliases for one canonical term without accidentally overwriting earlier aliases. Do not turn every sentence edit into a global replacement.
- Rank relevant terms and enforce a tokenizer-based prompt budget with reserved room for decoder control tokens. Measure a budget rather than assuming 50 words fit all languages. Avoid sending the same glossary through multiple mechanisms blindly.
- Compare bounded `initial_prompt` and supported `hotwords` behavior using the installed faster-whisper API. Hints are preferences, not guarantees; include negative samples where a hinted word should not appear.
- Do not use broad automatic replacement to repair uncertain sounds, negations, amounts or names. Preserve source text when ambiguous and offer an explicit correction.
- Separate native script, romanization and translation. Hinglish output is a preference to implement and test, not a consequence of selecting both English and Hindi. Evaluate Tamil/Malayalam romanization separately rather than assuming one spelling convention.

Acceptance: exact developer tokens improve on held-out examples without new substitutions in negative examples; word deletion persists; selected terms do not leak into unrelated languages/apps; no audio/transcript history or external requests are introduced.

### PR 4 — Bounded voice editing, not an agent

First ship deterministic editing in FlowPilot's own Scratchpad, where the document and selection are known. Then enable supported external editors only after target/selection verification tests. Terminal content is especially sensitive: never submit Enter or execute a command as part of editing.

Ordinary dictation and editing have distinct UI states and user-selected shortcuts. Saying an instruction while dictating documentation must not unexpectedly alter existing text. Existing spoken punctuation/self-correction behavior needs an explicit literal mode and regression coverage.

| Spoken request in edit mode | Allowed behavior |
| --- | --- |
| Replace Friday with Monday | Replace the unique matching span inside the selected scope; show the intended change. If several matches exist, ask which one. |
| Remove this part | Require an active verified selection; preview deletion. Without a selection, request clarification instead of guessing. |
| Add this sentence at the end | Append within the selected/owned document, not an arbitrary foreground app. |
| Make this shorter / more professional | Produce a local draft and diff for review; do not claim an unavailable model performed the instruction. |
| Undo that edit | Undo only the recorded transaction if the target revision still matches; otherwise present recovery text. |

Implement an edit transaction containing target identity, selected range, source revision/hash, instruction, validated operation, candidate result and one-use transaction ID. Revalidate target and selection immediately before apply. A changed document, unknown focus, password field, duplicate callback or unavailable context must leave the target unchanged. Empty replacement is valid only for an explicitly confirmed delete, not confused with model failure.

Preserve numbers, dates, identifiers and negations outside the explicitly authorized change. An instruction changing Friday to Monday is an allowed local delta, not permission to disable FactGuard for the entire document. Rephrasing still needs human review; token guards cannot prove meaning preservation.

Audit the existing `TransformsEngine` before reuse:

- Unsupported custom instructions currently fall through to concise formatting. Replace that behavior with a typed unsupported/unavailable result.
- Clipboard-based selection reads require the same sequence/ownership discipline as insertion, including success, timeout, empty clipboard and concurrent user-copy cases.
- Carry the full `InjectionResult`; do not equate dispatched/unverified text with a confirmed edit or issue a second injection after an uncertain first attempt.
- Current `revert_last_transform()` reuses injection rather than a verified inverse edit transaction. Do not advertise reliable undo until the range/revision behavior is proven.
- Failed FactGuard checks must block apply; an informational boolean alone is not an enforcement boundary.

For external field access, read only the expressly selected/necessary text, exclude secure fields, and bound context acquisition to 500 ms. A worker timeout must actually isolate a blocked accessibility call; merely abandoning a Python future does not cancel COM. Fail closed without blocking the Qt event loop. Do not add screenshot collection or workspace-wide scanning to this sprint.

### PR 5 — Optional local language model for richer wording

Reuse `engine/local_llm.py` rather than adding cloud APIs or a general agent runtime. A compact instruction model such as [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B) is a candidate for explicit rewriting, not a proven four-language winner. Test quantized, bounded, non-thinking inference on this CPU with native-speaker review; do not assume a published multilingual count guarantees Tamil/Malayalam editing quality.

Requirements before enabling:

- Explicitly installed local weights and selected model identity; do not silently use the first model returned by a server.
- Verify the backend runs locally and does not forward prompts or download assets. A loopback HTTP address alone does not prove the server is offline. Preserve the current proxy/redirect protections and test backend egress separately.
- Bounded input/output, a total wall-clock deadline across health checks and fallbacks, cancellation, one request owner, and no work on the GUI thread. A timeout leaves text unchanged.
- Structured, validated operations or a preview draft, never executable code/tools. Treat document instructions as data, not authority to run commands.
- Load only on demand; measure competition with ASR for CPU and RAM. Keep ordinary F9 dictation usable without this optional model.

No universal sub-1.5-second promise for rich CPU rewrites. Measure this mode separately from basic dictation and show progress/cancel honestly.

### PR 6 — Pilot, then decide whether fine-tuning is justified

Ask 5–10 target users to complete real writing tasks, including native speakers of the supported languages. Measure correction effort and successful task completion, not only whether a unit suite passed. Label languages as experimental, pilot-validated or release-qualified using disclosed evidence; do not mark all model-supported languages equally mature.

Only propose fine-tuning if repeatable acoustic errors remain after capture checks, model comparison and vocabulary improvements. Prepare an explicit, consented training corpus; split by speaker/session and phrase; retain a locked multilingual holdout. Compare a small pilot learning curve before committing to large collection or training cost. There is no universal hour count that guarantees improvement.

Training may require a separate GPU-equipped local/offline development machine; that does not change the CPU-only runtime requirement. Verify conversion to CTranslate2 and INT8 against the same tests. Check both gains in the target language and regressions elsewhere. Do not ship adapted weights simply because training loss declined. [Fine-tuning procedure](https://huggingface.co/blog/fine-tune-whisper), [CTranslate2 conversion support](https://opennmt.net/CTranslate2/guides/transformers.html#whisper)

## Companion work stays a separate, small track

Reuse the existing Companion Studio/shared native renderer and [desirability research](COMPANION_DESIRABILITY_RESEARCH.md). Offer a small original family with editable colors, accessories and expressions, reduced motion, a quiet mode, and a clear listening/processing/recovery pose.

For distributed packs, use owned/licensed assets and original characters rather than assuming permission for Naruto, Harry Potter or Star Wars names, logos or recognizable character designs. Broad original fantasy, ninja-adventure and space themes can be explored without copying a franchise. Any branded collaboration needs a separate licensing review before publication. User imports still need provenance and safe package handling; they are not a justification to bundle copied packs.

Test whether people choose and retain a companion separately from dictation quality. Avoid mandatory streaks, guilt mechanics or extra transcript collection. Cosmetics must not take focus, consume the speech CPU budget or delay insertion.

## First implementation handoff and definition of done

Start with PR 1 and the measurement foundation in PR 2. Do not simultaneously replace ASR, introduce an LLM and change formatting; that would hide which change helped or hurt. PR 3 follows the baseline. PR 4 begins in the owned Scratchpad; PR 5 is optional and only follows safe editing contracts. Companion work must not block those foundations.

Before promoting a candidate:

1. All affected behavioral tests and the repository's full regression runner report actual passed/skipped/failed counts. Interactive Windows tests run where focus can be verified; skips do not become passes.
2. A frozen human-voice evaluation shows improvements by language and difficulty group. Proposed promotion rule: at least 10% relative error reduction in the targeted group with no material critical-fact regression; inspect uncertainty and native-speaker judgments before accepting a small-sample result. This is a decision threshold, not an achieved result.
3. Normal short dictation still targets p95 below 1.5 seconds from speech end to visible text on the declared machine. If a higher-quality model misses that, expose a clearly labeled quality option rather than changing the default or the latency definition.
4. Editing tests cover ambiguous references, literal instructions, authorized versus unauthorized fact changes, wrong/unknown focus, stale selection, user clipboard updates, unavailable model, secure fields, duplicate apply, cancellation and guarded undo. Destructive/ambiguous edits require review.
5. Verify the exact packaged build offline with isolated config/cache, provisioned model assets and runtime egress instrumentation. Do not infer byte-level network proof from a success log line. Publish model/license/build provenance and known limitations.

Work completed for this plan: read-only implementation review, primary-source research, and mocked diagnostics for missing language entries, stale model cache and unsupported-edit fallback. No real speech accuracy benchmark, full regression run, model download, microphone recording, app behavior change, commit, push or release publication was performed for this document.
