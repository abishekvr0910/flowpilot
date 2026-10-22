# FlowPilot Real-Voice Multilingual Evaluation Corpus & Schema (PR 2)

**Status:** Implementation Specification & Initial Development Manifest  
**Inspected Baseline:** `115d2c1` (Post-PR 1)  
**Target Languages:** English (`en`), Hindi (`hi`), Tamil (`ta`), Malayalam (`ml`), plus German (`de`), Spanish (`es`) and French (`fr`) — the last three added 2026-10-22 for the real-voice baseline in [`DE_ES_FR_REAL_VOICE_BASELINE.md`](DE_ES_FR_REAL_VOICE_BASELINE.md).

**Review correction (2026-10-21):** These 40 entries are text-only recording
prompts, not an acoustic dataset. The original evaluation runner substituted
reference text for missing audio. Its zero-WER report was invalid and has been
superseded. No language accuracy or latency conclusion follows from these prompts.
Missing audio now produces `missing_audio`, null scores and an incomplete run
(CLI exit 2), without loading the recognizer. Failures are not scored as empty
transcriptions. Recorded audio requires explicit consent. Relative audio paths
are resolved against the manifest directory, not the current working directory.
Default reports go to ignored `scratch/evaluation/`; transcript inclusion requires
`--include-text`. Keep real participant recordings and references private.

---

## 1. Ethical, Privacy & Consent Invariants

1. **Strictly Consented Audio Only:** Only explicitly consented, deliberately recorded evaluation utterances may be stored.
2. **Never-Store Operating Default:** Passive microphone collection, clipboard watching, and everyday dictation harvesting remain hard-disabled. Everyday usage remains 100% ephemeral in volatile memory.
3. **Private Corpus Storage Isolation:** Raw evaluation audio files must reside exclusively in gitignored directories (`private/corpus/` or `data/corpus/`). Only authorized, redistributable manifest metadata and aggregate benchmark results may be committed to version control.
4. **Zero Cloud Egress:** All acoustic evaluation runs 100% locally on CPU via faster-whisper without internet queries or telemetry uploads.

---

## 2. Corpus Item Schema Specification

Each evaluation trial is defined by the following typed JSON schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FlowPilotCorpusItem",
  "type": "object",
  "required": [
    "item_id",
    "language",
    "group",
    "spoken_reference",
    "formatted_reference",
    "speaker_id",
    "consent_verified"
  ],
  "properties": {
    "item_id": {
      "type": "string",
      "description": "Unique identifier (e.g. 'ta-02-mixed')"
    },
    "language": {
      "type": "string",
      "enum": ["en", "hi", "ta", "ml", "de", "es", "fr"],
      "description": "ISO 639-1 language code"
    },
    "group": {
      "type": "string",
      "enum": ["clean", "developer_code", "mixed_script", "low_volume", "noise", "quantities"],
      "description": "Acoustic or domain difficulty group"
    },
    "spoken_reference": {
      "type": "string",
      "description": "Verbatim transcript of words actually spoken (for raw ASR WER)"
    },
    "formatted_reference": {
      "type": "string",
      "description": "Independently approved desired written text (for Formatted Quality Score)"
    },
    "speaker_id": {
      "type": "string",
      "description": "Anonymized speaker identifier"
    },
    "consent_verified": {
      "type": "boolean",
      "description": "True if participant signed written evaluation consent"
    },
    "audio_file": {
      "type": ["string", "null"],
      "description": "Relative path to local WAV fixture (16kHz 16-bit mono PCM)"
    },
    "duration_sec": {
      "type": "number",
      "description": "Audio duration in seconds"
    },
    "critical_entities": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of essential tokens (numbers, negations, code identifiers) that must be preserved"
    }
  }
}
```

---

## 3. Evaluation Metric Definitions

| Metric | Calculation Method | Rationale & Distinction |
| :--- | :--- | :--- |
| **Raw WER** | `(Substitutions + Deletions + Insertions) / Total Spoken Tokens` | Measures acoustic recognition against verbatim `spoken_reference`. Uses language-aware tokenization that preserves Indic script boundaries. |
| **Unicode CER** | Character edit distance `/ Total Non-Space Characters` | Unicode NFC normalized. Retains Indic combining marks (viramas, vowel signs) without stripping codepoints. |
| **Critical Entity Accuracy** | Matched occurrences `/ max(reference count, hypothesis count)` | Exact numeric, negation and identifier tokens, including duplicates and additions. The preservation flag also checks order. This heuristic is not complete semantic or date-understanding validation; review annotated critical facts separately. |
| **Formatted Quality Score** | `1.0 - min(1.0, WER(desired_reference, hypothesis))` | Evaluates post-processed written quality against `formatted_reference`. Never conflated with raw ASR accuracy. |
| **Measured duration** | `T_decode`, `T_format` | Monotonic WAV processing durations. First decode includes lazy model load. Does not measure OS insertion or stop-to-visible-text latency. |
| **Sampled Memory** | Initial and final process-tree RSS via `psutil` | Two samples, not peak usage or evidence against transient spikes. |

---

## 4. Development Smoke Corpus (40 Items)

The initial smoke evaluation dataset ([`docs/evaluation/DEV_SMOKE_CORPUS_MANIFEST.json`](DEV_SMOKE_CORPUS_MANIFEST.json)) defines 40 balanced items:

All audio paths are currently null. Durations in the original template were
estimates, not measurements. Record consented clips before using this matrix for
model comparison. The runner does not independently capture network traffic.

- **English (`en`):** 10 items (clean conversational, git commands, URLs, quantities, noise, negations).
- **Hindi (`hi`):** 10 items (native script, mixed English code-switching, server restart commands, dates, negations).
- **Tamil (`ta`):** 10 items (native script, React/Docker technical code-switching, FastAPI identifiers, quantities, negations).
- **Malayalam (`ml`):** 10 items (native script, Node.js/Kubernetes mixed-script, PostgreSQL queries, quantities, negations).

---

## 5. Model Promotion Decision Rule

Before promoting a challenger model (e.g., multilingual `small` over `base`):
1. **Error Reduction Threshold:** Must achieve at least a **10% relative error reduction** in raw WER/CER on targeted language/difficulty groups compared to baseline.
2. **Fact Retention Safety:** Critical fact preservation accuracy must remain **>= 98.0%** (zero tolerance for dropping negations or corrupting numbers).
3. **Latency Bound:** P95 stop-to-visible-text latency on host CPU must remain within **1.5 seconds** for standard short dictation (< 5s speech duration).
