# 0006. ONNX Runtime Multilingual Specialist ASR Harness

**Date:** 2026-11-02 (Updated 2026-11-04 for v3.1.3)  
**Status:** Implemented for Tamil (`indicconformer-ta`); Polish (`small` Provisioned, `Parakeet-TDT` Planned for v3.2)  
**Audience:** FlowPilot maintainers, Core Engineers  
**Target Milestone:** v3.1.x (Tamil Specialist + Polish Provisioning) / v3.2.0 (Parakeet-TDT Evaluation)  
**Dependencies:** `onnxruntime>=1.16.0` (existing requirement), `docs/evaluation/TAMIL_POLISH_BENCHMARK_CORPUS.json`  

---

## 1. Executive Summary & Problem Declaration

While Whisper (`base` / `small` via `faster-whisper` CTranslate2) provides reliable multilingual transcription for high-resource Latin languages, its acoustic accuracy and tokenization latency on low-to-medium resource languages—particularly **Tamil** (`ta`) and **Polish** (`pl`)—exhibit known limitations:
1. **Tamil Acoustic Degradation in Base Whisper:** Sub-optimal recognition of complex conjuncts, geminates, and colloquial code-switching ("Tanglish"), frequently hallucinating English phonetic approximations or dropping retroflexes (`ழ`, `ள`, `ற`).
2. **Polish Diacritic and Case Inflection Errors:** Whisper base frequently strips or confuses Slavic diacritics (`ą`, `ć`, `ę`, `ł`, `ń`, `ó`, `ś`, `ź`, `ż`), causing severe FactGuard validation penalties.
3. **The Cloud vs Local Dilemma:** Commercial competitors rely on expensive cloud speech APIs (OpenAI Whisper Large v3, Azure Speech, Google Chirp). FlowPilot strictly enforces the **Zero Cloud Egress Invariant**: dictation audio, tensors, and transcripts must remain 100% on the user's host machine.

This specification establishes the architecture for an offline **ONNX Runtime Specialist ASR Harness** (`engine/onnx_asr/`) designed to evaluate and host specialized local models without cloud dependence or recurring API expenses.

---

## 2. Evaluation Target Models & Delivery Status

| Language | Target Specialist Model | Original Architecture | Quantized Target | Size on Disk | Delivery Status (v3.1.3) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tamil (`ta`)** | **IndicConformer Medium (~120M parameters)** (AI4Bharat) | Conformer-CTC | ONNX INT8 Dynamic | 137 MB (131 MiB) | **Shipped (On-Demand via Settings / Setup Wizard):** Provisioned from `models-v1` into `~/.flowpilot/models/indicconformer-ta` with SHA-256 verification and NeMo-exact Slaney + `preemph=0.97` frontend. |
| **Polish (`pl`)** | **Whisper Small** (Current) / **Parakeet-TDT 0.6B** (v3.2 Target) | Encoder-Decoder / FastConformer-TDT | CTranslate2 INT8 / ONNX INT8 | 461 MB / ~590 MB | **Whisper Small Provisioned in UI (18.0% WER vs 49.6% on Base):** 1-click download in Settings & Setup Wizard; `Parakeet-TDT` tracked for v3.2 evaluation. |
| **Bundled Default** | **Whisper Base** (OpenAI / CTranslate2) | Encoder-Decoder Transformer | CTranslate2 INT8 | 141 MB | **Bundled in Installer:** Immediate zero-download English & high-resource language baseline. |

---

## 3. Architecture & Execution Pipeline

```
[Raw Audio PCM (16 kHz, 16-bit Mono; Pure-NumPy Resampled if 44.1/48 kHz)]
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ NeMo-Exact Audio Preprocessing (< 15 ms, Pure NumPy)   │
│ • Pre-emphasis filter (0.97) + centered Hann STFT      │
│ • Slaney-scale, area-normalized 80-bin log-mel         │
│ • Per-channel CMVN normalization                       │
└────────────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ ONNX Runtime Engine (`engine/onnx_asr/harness.py`)     │
│ • Execution Provider: CPUExecutionProvider (AVX2/AVX512│
│ • Resolves ~/.flowpilot/models, FLOWPILOT_MODEL_DIR,   │
│   and dev models/ across source and frozen .exe builds │
│ • INT8 Dynamic Quantization (Zero FP32 overhead)       │
└────────────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ Specialist Decoder & Language Post-Processing          │
│ • CTC Greedy Decoding + Tamil Unicode Boundary Repair  │
│ • Dynamic Custom Vocabulary & Phonetic Alias Biasing   │
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

1. **Zero Cloud Egress:** All model weights, vocabulary files, audio arrays, and transcripts remain strictly in local storage (`~/.flowpilot/models/` or `models/`). Model downloads occur solely via explicit user-initiated setup actions with SHA-256 verification.
2. **Latency Budget (Consumer CPU):**
   - Real-Time Factor (RTF) must not exceed **0.35x** on a modern 8-core x86_64 CPU (AVX2 enabled). Measured IndicConformer latency averages **~0.68s** per clip (~4.2x faster than Whisper Small).
3. **RAM Memory Budget:**
   - Active process working set footprint must remain under **1.2 GB RSS** during peak decoding; IndicConformer preloads conditionally only when active language is `ta` or `auto`.
4. **Deterministic FactGuard Compliance:**
   - All critical numbers, currency, dates, code identifiers, and negations (`இல்லை`, `வேண்டாம்`, `nie`, `nigdy`) must preserve entities deterministically without hallucination.

---

## 5. Benchmark & Validation Protocol

The specialist models are benchmarked against both Mozilla Common Voice human ground truth (`docs/evaluation/TAMIL_POLISH_INDEPENDENT_ACCURACY_REPORT.md`) and the 100-sentence manifest in [`docs/evaluation/TAMIL_POLISH_BENCHMARK_CORPUS.json`](../evaluation/TAMIL_POLISH_BENCHMARK_CORPUS.json):
- **Raw Acoustic WER & CER:** Evaluated on Mozilla Common Voice 17.0 clips and casual real-voice recordings.
- **Code-Switching Accuracy:** Evaluated on mixed colloquial English loanwords and developer terms (`Docker`, `Git`, `Python`, `Kubernetes`, `lunchukku`, `correct-aana`).
- **Dual-Mode Transliteration:** Verified with `engine/transliteration.py` for Tamil script vs Tanglish output.
- **Diacritic Integrity:** Verified on Polish Slavic nasal vowels and sibilants.
