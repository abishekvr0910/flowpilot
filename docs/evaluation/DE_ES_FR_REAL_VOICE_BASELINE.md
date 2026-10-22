# FlowPilot Real-Voice Multilingual Baseline — de / es / fr

**Date:** 2026-10-22
**Status:** Measured. Replaces the withdrawn `0.00%` and `95.24%` figures.
**Corpus:** 120 consented real-human-speech clips (40 de / 40 es / 40 fr)
**Models:** `faster-whisper base` (production default) and `faster-whisper small`
**Measurement path:** fully offline, zero egress, CPU (int8, 8 threads)

---

## 1. Why this document exists

Two numbers about non-English dictation were circulating in the repository and
neither survived scrutiny:

| Number | Where it came from | Why it was withdrawn |
|---|---|---|
| **0.00% WER** | `docs/archive/FLOWPILOT_LANGUAGE_VALIDATION.md`, and the Day 28–29 pilot case study | It was the *negation-safety* sub-metric over 47 words, relabelled as overall accuracy. The same table's "Polish Latency 0.0–1.5 ms" was the orthography transform, not recognition. |
| **95.24% WER** | `docs/release/FLOWPILOT_V302_RELEASE_REPORT.md`, German | Measured on **2 synthetic SAPI-TTS cases** (21 reference words). Too small and too synthetic to describe the product. |

This document replaces both with a measurement on **real human speech**, with
exact denominators, and states what the numbers do and do not support.

---

## 2. Provenance and consent

| Property | Value |
|---|---|
| Source | Mozilla **Common Voice 17.0**, `validation` split only |
| Mirror | `fixie-ai/common_voice_17_0` on the Hugging Face Hub |
| Licence | Common Voice audio is published by Mozilla under **CC0**; contributors consented to publication at recording time |
| `consent_verified` | `true` for every item, on that basis |
| Speaker identity | **Anonymised** — the manifest carries `cv-anon-<lang>`, never a contributor identifier |
| Quality filter | `down_votes == 0`, `up_votes >= 2`, `locale == <lang>`, unique sentence, 15–200 characters |
| Critical-entity mix | 20 of 40 clips per language deliberately carry a negation or a number so the fact-retention gate has real coverage; the other 20 are plain declarative speech |
| Audio storage | `private/corpus/<lang>/*.wav`, 16 kHz mono PCM16, **gitignored** (`private/`) |
| Manifest | `docs/evaluation/DE_ES_FR_REAL_VOICE_MANIFEST.json` — metadata only, committable |
| Audio on disk | 21.0 MB total |

Acquisition is a **separate, one-off data-preparation step**
(`scripts/acquire_real_voice_corpus.py`). The measurement path itself
(`benchmarks/run_real_voice_eval.py`) performs no network access.

---

## 3. Results

Mean item WER is the mean of the per-item WER, the same statistic the runner
reports. Token-weighted WER divides total errors by total reference words and
is the more conventional corpus-level figure; it is lower because short
sentences with a single error score near 100% WER.

### 3.1 `faster-whisper base` (production default)

| Language | Items | Ref. words | WER (mean item) | WER (token-weighted) | CER | Formatted quality | Decode p50 | Decode p95 |
|---|---|---|---|---|---|---|---|---|
| **de** | 40 | 367 | **20.17%** | 18.54% | 7.32% | 0.798 | 0.65 s | 0.79 s |
| **es** | 40 | 383 | **21.41%** | 20.10% | 8.75% | 0.784 | 0.66 s | 0.73 s |
| **fr** | 40 | 433 | **29.04%** | 27.45% | 11.19% | 0.710 | 0.67 s | 0.74 s |

### 3.2 `faster-whisper small`

| Language | Items | Ref. words | WER (mean item) | WER (token-weighted) | CER | Formatted quality | Decode p50 | Decode p95 |
|---|---|---|---|---|---|---|---|---|
| **de** | 40 | 367 | **9.01%** | 9.29% | 3.49% | 0.910 | 2.12 s | 2.40 s |
| **es** | 40 | 383 | **13.46%** | 9.92% | 5.28% | 0.876 | 2.19 s | 2.33 s |
| **fr** | 40 | 433 | **19.66%** | 17.60% | 7.50% | 0.812 | 2.22 s | 2.42 s |

### 3.3 Critical-entity retention (the fact gate)

Counts are entities, not items. "Exact" is the number of items where the
reference and the hypothesis entity sets were identical.

| Language | Model | Entities kept | Accuracy | Items exact |
|---|---|---|---|---|
| **de** | base | 21 / 22 | 95.45% | 39 / 40 |
| **de** | small | 21 / 22 | 95.45% | 39 / 40 |
| **es** | base | 24 / 26 | 92.31% | 37 / 40 |
| **es** | small | 26 / 26 | **100.00%** | 39 / 40 |
| **fr** | base | 20 / 27 | 74.07% | 35 / 40 |
| **fr** | small | 26 / 27 | 96.30% | 39 / 40 |

**Every individual failure, with the entity that moved:**

| Item | Language | Model | Missing | Added | Reference |
|---|---|---|---|---|---|
| de-cv-036 | de | base | `kein` | — | "Da kriegst du kein Gehalt, nur eine Aufwandsentschädigung." |
| de-cv-035 | de | small | `keine` | `keiner` | "Keine der beiden Loks ist erhalten geblieben." |
| es-cv-022 | es | base | `sin` | — | "Sin embargo, hay más versiones sobre las raíces del bollo de verde." |
| es-cv-039 | es | base | — | `10` | "Sin embargo, en dicho Tour, los ojos estaban puestos en 'el Diablo'." |
| fr-cv-029 | fr | both | `sans` | — | "Le bassiste Rico quitte le groupe, qui doit jouer sans bassiste." |
| fr-cv-032 | fr | base | `ne` | — | "De celui de Reventlou et Beseger ne subsiste que l'obélisque." |
| fr-cv-035 | fr | base | `ne` | — | "Ou si tu ne veux pas trop attirer l'attention." |
| fr-cv-038 | fr | base | — | `4` | "Une démarche de catcheur slave n'est pas adoucie par de jolis talons vernis." |
| fr-cv-017 | fr | base | — | `1` | — |

Two of these are worth reading carefully:

* **de-cv-035** (`keine` → `keiner`) is a **morphological** change, not a lost
  negation. The gate uses strict token equality, so it counts as a failure even
  though the meaning survives. This is the gate working as specified, and it
  is the single reason German does not clear 98% for either model.
* The `added` cases (fr-cv-038 `4`, fr-cv-017 `1`) are the recogniser
  rendering a quantity as a digit where the reference spelled it, or
  introducing one. They are recorded separately from `missing` so a reviewer
  can tell a **dropped** fact from an **added** one.

---

## 4. Model promotion decision rule

`docs/evaluation/REAL_VOICE_CORPUS_SCHEMA.md` §5 defines three gates. Verdict
against the measured evidence:

### Gate 1 — ≥ 10% relative error reduction

| Language | base | small | Reduction | Verdict |
|---|---|---|---|---|
| de | 20.17% | 9.01% | **55.3%** | **PASS** |
| es | 21.41% | 13.46% | **37.1%** | **PASS** |
| fr | 29.04% | 19.66% | **32.3%** | **PASS** |

### Gate 2 — critical fact preservation ≥ 98.0%

| Language | base | small | Verdict (small) |
|---|---|---|---|
| de | 95.45% | 95.45% | **FAIL** (21/22, one morphological mismatch) |
| es | 92.31% | **100.00%** | **PASS** (26/26) |
| fr | 74.07% | 96.30% | **FAIL** (26/27, one dropped `sans`) |

**Gate 2 is not satisfied on the available evidence.** Note the denominators:
22–27 entities. That is far too small to certify a 98% rate in either
direction, so the honest statement is *"not met as measured, and not
certifiable from this sample"* — not *"the model is unsafe"*. A larger
entity-bearing sample is required before this gate can be called either way.

### Gate 3 — P95 stop-to-visible-text ≤ 1.5 s

**NOT MEASURED by the runner.** `benchmarks/run_real_voice_eval.py` measures
WAV decode and formatting only, and says so in its own output
(`latency_boundary: "WAV decode + formatting only; first decode includes lazy
model load; no OS injection"`).

What can be said from the decode timings alone:

* `base` decode p95 is 0.73–0.79 s. Stop-to-visible-text is decode +
  formatting + injection, so `base` is **plausibly** inside the 1.5 s bound but
  **is not verified**.
* `small` decode p95 is **2.33–2.42 s**. Decode alone already exceeds the
  1.5 s bound, so **`small` cannot satisfy Gate 3** no matter how the rest of
  the pipeline performs.

---

## 5. Verdict

**Do not promote `small` on this evidence.** It wins decisively on accuracy
(32–55% relative WER reduction, and the best fact retention of any
configuration measured) but its decode latency alone busts the 1.5 s bound
that the promotion rule sets. `base` stays the production default for now.

**The accurate statement about non-English dictation today, for a pilot:**

| Language | Production (`base`) read-speech WER |
|---|---|
| German | ~20% |
| Spanish | ~21% |
| French | ~29% |

**These are floors, not expectations.** The corpus is deliberately the easiest
condition available:

* single, **read** sentences — no disfluencies, no false starts, no
  self-corrections, no fillers;
* one speaker, no overlap, no crosstalk;
* quality-filtered (community up-votes), so no heavy noise or clipping;
* ~370–430 reference words per language, which supports a **direction** and a
  regression guard, not a certification.

Real dictation adds disfluency, restarts, self-correction, room acoustics
and overlap. Expect materially worse numbers in live use. The previous
synthetic evaluation could not show this because it never contained a human
voice.

---

## 6. Measurement-instrument defects found and fixed

Three defects were found **in the metric code** while running this baseline.
All three would have produced a *false pass* on the fact gate for exactly the
languages under test. They are fixed in `engine/evaluation_metrics.py`:

1. **`NEGATION_DICTIONARY` had no `de`, `es` or `fr` entries.** Only `en`,
   `hi`, `ta` and `ml` existed, and the lookup used the raw language string,
   so `NEGATION_DICTIONARY.get("de", [])` returned an empty list. German and
   French negations were therefore never extracted, and a dropped `nicht` or
   `pas` was invisible to the gate. Spanish was only partly covered because
   `no` happens to be in the English list. The lookup now also tolerates
   locale codes such as `de-DE`.
2. **Spanish inverted marks and curly quotes were not stripped from tokens.**
   The edge-punctuation class was `[.,!?;:()[\]{}\"\'«»]`, missing `¡`, `¿`,
   `„`, `“`, `”`, `‘`, `’`. A sentence beginning `¡Nunca!` tokenized as
   `¡nunca`, so the negation was not detected.
3. **A number spelled out in the reference and rendered as a digit by the
   recognizer looked like a dropped number plus a hallucinated one.** The
   reference "Veintidós" against a hypothesis of "22" compared unequal, so
   the same fact counted twice against the model. Number words for
   en/de/es/fr are now normalised to digits before comparison.

Defect 1 alone would have let the earlier run report a clean fact-retention
pass for German and French on a sample where the gate was measuring an empty
set.

`benchmarks/run_real_voice_eval.py` now also records `missing_critical` and
`added_critical` per trial, so a dropped fact and an added one are
distinguishable in the report rather than both collapsing into one accuracy
number.

---

## 7. Reproduction

```powershell
# 1. Acquire the corpus (network; one-off; writes gitignored audio)
python -X utf8 scripts\acquire_real_voice_corpus.py

# 2. Measure (offline, zero egress)
python -X utf8 benchmarks\run_real_voice_eval.py `
    --manifest docs\evaluation\DE_ES_FR_REAL_VOICE_MANIFEST.json `
    --model base  --output scratch\evaluation\desfr_base.json
python -X utf8 benchmarks\run_real_voice_eval.py `
    --manifest docs\evaluation\DE_ES_FR_REAL_VOICE_MANIFEST.json `
    --model small --output scratch\evaluation\desfr_small.json
```

The runner exits **0** only when every item was measured; `missing_audio`,
`consent_required` and `failed` all produce exit **2** and null scores. A
partial run cannot be mistaken for a complete one.

Models are resolved from `models/faster-whisper-<size>` with
`local_files_only=True`; no weights are fetched at measurement time.

---

## 8. What is still missing

| Gap | Why it matters | Suggested next step |
|---|---|---|
| **Stop-to-visible-text is not measured** | Gate 3 cannot be evaluated, and `base` vs `small` latency cannot be compared on the metric that actually matters | Add an injection-path timing harness, or state the decode-only bound explicitly in the promotion rule |
| **No spontaneous-speech corpus** | Read sentences are the easiest case; dictation is the product | Record consented dictation sessions (the `private/corpus/` layout and the consent flags already exist for this) |
| **No noise / overlap / low-volume groups** | `group` in the manifest supports them; Common Voice does not supply them | Record them locally with the same consent flow |
| **Sample too small for the fact gate** | 22–27 entities cannot certify 98% | Enlarge the entity-bearing slice to several hundred entities per language |
| **English not re-baselined on this corpus** | The gate comparison is incomplete without a reference point | Run the same corpus shape for `en` |
| **No baseline for `hi` / `ta` / `ml`** | The schema still claims those languages | Same treatment, or narrow the schema's claim |

---

## 9. Related documents

* `docs/evaluation/REAL_VOICE_CORPUS_SCHEMA.md` — schema, metric definitions, promotion rule
* `docs/evaluation/DE_ES_FR_REAL_VOICE_MANIFEST.json` — the corpus manifest (metadata only)
* `docs/evaluation/DEV_SMOKE_CORPUS_MANIFEST.json` / `DEV_SMOKE_EVAL_REPORT.json` — the en/hi/ta/ml template corpus, still `missing_audio`
* `docs/archive/FLOWPILOT_LANGUAGE_VALIDATION.md` — withdrawal notice for the 0.00% claim
* `docs/release/FLOWPILOT_V302_RELEASE_REPORT.md` — the audited synthetic numbers this supersedes
* `engine/evaluation_metrics.py` — metric definitions and the three fixes in §6
* `benchmarks/run_real_voice_eval.py` — the measurement runner
* `scripts/acquire_real_voice_corpus.py` — corpus acquisition
