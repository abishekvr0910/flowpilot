# 0006. ONNX Runtime Multilingual Specialist ASR Harness

**Date:** 2026-11-02  
**Status:** Architecture Specification & Benchmark Protocol  
**Audience:** FlowPilot maintainers, Core Engineers  
**Target Milestone:** v3.2.0 Multilingual Acoustic Leapfrog  
**Dependencies:** `onnxruntime>=1.16.0` (existing requirement), `docs/evaluation/TAMIL_POLISH_BENCHMARK_CORPUS.json`  

---

## 1. Executive Summary & Problem Declaration

While Whisper (`base` / `small` via `faster-whisper` CTranslate2) provides reliable multilingual transcription for high-resource Latin languages, its acoustic accuracy and tokenization latency on low-to-medium resource languages—particularly **Tamil** (`ta`) and **Polish** (`pl`)—exhibit known limitations:
1. **Tamil Acoustic Degradation in Base Whisper:** Sub-optimal recognition of complex conjuncts, geminates, and colloquial code-switching ("Tanglish"), frequently hallucinating English phonetic approximations or dropping retroflexes (`ழ`, `ள`, `ற`).
2. **Polish Diacritic and Case Inflection Errors:** Whisper base frequently strips or confuses Slavic diacritics (`ą`, `ć`, `ę`, `ł`, `ń`, `ó`, `ś`, `ź`, `ż`), causing severe FactGuard validation penalties.
3. **The Cloud vs Local Dilemma:** Commercial competitors rely on expensive cloud speech APIs (OpenAI Whisper Large v3, Azure Speech, Google Chirp). FlowPilot strictly enforces the **Zero Cloud Egress Invariant**: dictation audio, tensors, and transcripts must remain 100% on the user's host machine.

This specification establishes the architecture for an offline **ONNX Runtime Specialist ASR Harness** (`engine/onnx_asr/`) designed to evaluate and host specialized local models without cloud dependence or recurring API expenses.

---

## 2. Evaluation Target Models

| Language | Target Specialist Model | Original Architecture | Quantized Target | Size on Disk | Primary Strength |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tamil (`ta`)** | **IndicConformer-600M** (AI4Bharat) | Conformer-CTC / RNN-T | ONNX INT8 Dynamic | ~620 MB | Trained on 10,000+ hours of authentic Indian regional dialects; native Tamil phoneme boundary modeling. |
| **Polish (`pl`)** | **Parakeet-TDT 0.6B** (NVIDIA NeMo) | FastConformer-TDT | ONNX INT8 Dynamic | ~590 MB | Token-and-Duration Transducer (TDT); 3-4x faster decoding than standard autoregressive models with high diacritic precision. |
| **Fallback** | **Whisper Small** (OpenAI / CTranslate2) | Encoder-Decoder Transformer | CTranslate2 INT8 | 461 MB | General purpose bundled multilingual fallback. |

---

## 3. Architecture & Execution Pipeline

```
[Raw Audio PCM (16 kHz, 16-bit Mono)]
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ Audio Preprocessing & Feature Extraction (< 15 ms)     │
│ • Mel-spectrogram computation (80 or 128 mel bins)     │
│ • CMVN (Cepstral Mean and Variance Normalization)      │
└────────────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ ONNX Runtime Engine (`engine/onnx_asr/harness.py`)     │
│ • Execution Provider: CPUExecutionProvider (AVX2/AVX512│
│ • Windows Acceleration: DirectMLExecutionProvider (opt)│
│ • INT8 Dynamic Quantization (Zero FP32 overhead)       │
└────────────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ Specialist Decoder & Language Post-Processing          │
│ • CTC Greedy / Beam Search or TDT Duration Decoding    │
│ • Subword Tokenizer (SentencePiece / HuggingFace)      │
└────────────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ FlowPilot Output Adaptation Layer                      │
│ • For Tamil: `apply_transliteration_if_enabled`        │
│   (Preserves native script OR emits clean Tanglish)    │
│ • FactGuard Entity Preservation Verification           │
│ • Injection via TextInjector                           │
└────────────────────────────────────────────────────────┘
```

---

## 4. Operational Invariants & Resource Budgets

1. **Zero Cloud Egress:** All model weights, vocabulary files, audio arrays, and transcripts remain strictly in local storage (`assets/models/onnx/`). No remote telemetry or validation pings are permitted.
2. **Latency Budget (Consumer CPU):**
   - Real-Time Factor (RTF) must not exceed **0.35x** on a modern 8-core x86_64 CPU (AVX2 enabled). A 10-second audio stream must decode in under 3.5 seconds.
3. **RAM Memory Budget:**
   - Active process working set footprint must remain under **1.2 GB RSS** during peak decoding.
4. **Deterministic FactGuard Compliance:**
   - All critical numbers, currency, dates, code identifiers, and negations (`இல்லை`, `வேண்டாம்`, `nie`, `nigdy`) must score >= 98% entity preservation on the 100-sentence benchmark suite.

---

## 5. Benchmark & Validation Protocol

The specialist models will be benchmarked directly against the 100-sentence manifest defined in [`docs/evaluation/TAMIL_POLISH_BENCHMARK_CORPUS.json`](../evaluation/TAMIL_POLISH_BENCHMARK_CORPUS.json):
- **Raw Acoustic WER & CER:** Evaluated on conversational clean speech.
- **Code-Switching Accuracy:** Evaluated on mixed developer commands (Docker, Git, React, Kubernetes).
- **Dual-Mode Transliteration:** Verified with `engine/transliteration.py` for Tamil vs Tanglish output.
- **Diacritic Integrity:** Verified on Polish Slavic nasal vowels and sibilants.

Benchmark scripts will output structured verification receipts matching `docs/evaluation/DEV_SMOKE_EVAL_REPORT.json` standards.
