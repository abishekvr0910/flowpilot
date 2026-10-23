# Runtime performance evaluation

**Owner:** Voice evaluation, scope feature 25.
**Status:** Tooling and protocol implemented. Physical desktop, long session, and hardware class signoff remain pending.

## What each measurement means

| Measurement | Start | End | Limits |
|---|---|---|---|
| Desktop cold startup | Launch the recorded executable | Model ready and controls usable | Record process creation and readiness separately from first transcription |
| Cold processing | Deliver the first WAV buffer to an unloaded recognizer | Formatting completes | Includes lazy model load; does not include audio capture or insertion |
| Warm processing | Deliver a WAV buffer to the loaded recognizer | Formatting completes | Decode and formatting are recorded separately |
| Visible delivery | The user stops dictation | A new expected text span is observed in the intended document | Record target, sample count, failures, and confirmation method |
| Dispatch duration | The user stops dictation | Input dispatch completes | An unreadable target has no verified visible delivery endpoint |
| Process memory | Sample the same defined process tree | Sample after each stage | Sampled RSS is not peak memory and shared pages can be counted in multiple processes |
| Process CPU | CPU time before processing | CPU time after formatting | Aggregate CPU can exceed 100 percent when several cores work |

Source evaluator timings cannot establish packaged desktop performance. Synthetic speech cannot establish native speaker accuracy. Keep these groups separate.

Production `FlowOrchestrator` telemetry names the end of its current pipeline `injection_result`. Its visible-delivery field is `null` and marked `not_measured` until a target document observer records actual appearance. Do not graph the injection-result series as stop-to-visible latency.

## Existing evaluator

`benchmarks/run_real_voice_eval.py` records machine and model identity, cold and warm processing p50 and p95, process CPU time, and sampled process tree RSS. A model file fingerprint is included when its local path is available. Output excludes transcript text unless `--include-text` is explicitly requested.

```powershell
python -X utf8 benchmarks/run_real_voice_eval.py --manifest <consented-manifest.json> --model base --output scratch/evaluation/base-runtime.json
python -X utf8 benchmarks/run_real_voice_eval.py --manifest <consented-manifest.json> --model small --output scratch/evaluation/small-runtime.json
```

The default development manifest is a template. Missing recordings produce an incomplete result, not a simulated score. Use a fresh process for each model and keep offline model weights already provisioned. SAPI fixtures may be used for a clearly labelled processing smoke test.

The first inference is classified as cold according to the recognizer's actual loaded state. Warm quantiles exclude the cold inference. Quantiles use linear interpolation at `(sample_count - 1) * percentile / 100`; no valid samples means unknown, not zero. Counts and failures accompany every percentile. Small smoke samples do not establish a stable p95.

The evaluator explicitly leaves visible delivery, desktop startup, recording CPU, companion CPU, peak memory, and long session growth unmeasured. Those fields require the physical workflow below.

The first labelled source processing smoke measurements are in the [raw evidence record](../evaluation/RUNTIME_PROCESSING_SMOKE_2026-10-22.json) and [verification report](../reviews/2026-10-23-remediation-verification.md). They use one synthetic English utterance repeated eight times per model. They are a tool check, not a visible delivery, native speaker, or hardware support result.

## Hardware and model support matrix

Before trials, record CPU model, physical and logical core counts, installed RAM, Windows build, power mode, model weight hash, inference thread count, source or executable identity, and background workload.

| Class | Required evaluation | Signoff |
|---|---|---|
| Reference Windows developer PC | Default base model, short dictation and repeated bursts in target apps | Pending physical measurements |
| Multilingual quality profile | Small model, real English, Hindi, Tamil, and Malayalam speech | Pending real speaker and physical measurements |
| Lower resource Windows PC | Document actual CPU and RAM, compare eligible model choices | Pending access and measurements |

These are evaluation classes, not claims that every CPU family is supported. A measurement on one machine applies to that machine and workload.

## Physical evaluation and budgets

1. Freeze the candidate identity and declare the budgets for each hardware and model combination before reviewing results. Record required cold start, warm visible delivery, loaded and peak memory, and idle CPU budgets. Unfilled budgets remain an open release decision.
2. As the initial reference goal, evaluate the project's historical warm dictation target of about 1.2 seconds median and under 1.5 seconds p95 on a documented eight thread consumer host. This is a target to test, not an established result or a guarantee for small models or every PC.
3. Use at least 50 warm trials per selected target and model in the initial evaluation. Publish the sample size and treat this as an engineering evaluation, not proof of a 99.9 percent service guarantee. Record cold trials separately.
4. In Notepad, VS Code, Word, Chrome, and Terminal, measure the stop action and actual newly visible text. Keep verified insertion, unverified dispatch, safe refusal, manual recovery, and duplicates separate. Never retry an unverified send blindly.
5. Sample the same process tree through idle, recording, processing, and animation. State the sampling interval and whether the reported maximum is sampled or supplied by an OS peak counter.
6. Run a 30 minute session with repeated short bursts and a long utterance. Keep a queue and memory series after warmup. Investigate growing backlog, continuing memory growth, UI freezes, or missed audio before release.
7. Compare against the baseline recorded under matching conditions. If a model misses a declared budget, change its supported profile, improve the implementation, or retain the failed result. Do not silently redefine the metric.

Use non sensitive fixtures and keep text collection disabled by default. Do not alter the system audio defaults for ordinary testing. A missing interactive desktop blocks physical measurements and must be recorded as pending.

## Evidence for release

Attach the raw local report, corpus identity, hardware, model identity, source or binary identity, exact metric boundary, counts, failures, and budget decision to the [release evidence record](../release/RELEASE_EVIDENCE_TEMPLATE.md). Label source processing smoke results separately from the real speaker pilot and from packaged visible delivery.
