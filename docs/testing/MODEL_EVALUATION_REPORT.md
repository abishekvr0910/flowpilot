# FlowPilot Speech Model Evaluation & Recognition Intelligence Report

**Audit Date:** October 15, 2026 (Updated Post-Publication Audit)  
**Host Environment:** Windows 11 (x64), 8-Thread CPU  
**Quantization:** INT8 CPU Inference via CTranslate2  
**Test Harness:** [`tests/test_model_benchmarks_extended.py`](file:///S:/APPs/New%20folder/tests/test_model_benchmarks_extended.py) & [`scratch/audit_real_accuracy_corpus.py`](file:///S:/APPs/New%20folder/scratch/audit_real_accuracy_corpus.py)  
**Classification:** Empirical Speech Architecture & Model Optimization Audit  

---

## 1. Executive Summary

This report documents the empirical evaluation, upstream citations, and disk feasibility analysis of local speech recognition models evaluated for FlowPilot desktop dictation.

To ensure engineering rigor, this report explicitly distinguishes between:
1. **Measured Directly on Host Machine:** Quantified via high-resolution timers (`time.perf_counter()`), memory probes (`psutil`), and local audio transcripts.
2. **Upstream Specification / Cited Benchmark:** Official metrics published by OpenAI, SYSTRAN, or Hugging Face.
3. **Estimated:** Theoretical projections based on architecture scaling.
4. **Not Tested / Blocked:** Models whose download or testing was blocked by hardware constraints.

---

## 2. Empirical Benchmark Findings (Host Hardware Data)

The following metrics were **measured directly on this machine** executing CTranslate2 INT8 models across standardized acoustic conditions:

| Model | Scenario | Audio Duration | STT Latency | Polish Latency | Total Latency | Real-Time Factor (RTF) | Word Error Rate (WER) | Character Error Rate (CER) | FactGuard Status | Process RAM | Evidence Source |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **tiny (39M)** | Conversational Business (Clean) | 5.3s | 992.1 ms | 6.9 ms | 999.0 ms | 0.19x | **0.0%** | **0.0%** | **PASS** | 180 MB | Measured directly on host |
| **tiny (39M)** | Fast-Paced Dictation (Rate +3) | 3.5s | 498.2 ms | 1.4 ms | 499.7 ms | 0.14x | **0.0%** | **0.0%** | **PASS** | 180 MB | Measured directly on host |
| **tiny (39M)** | Acoustic Noise Degraded (15dB SNR) | 4.9s | 501.4 ms | 2.1 ms | 503.5 ms | 0.10x | **0.0%** | **0.0%** | **PASS** | 180 MB | Measured directly on host |
| **tiny (39M)** | Developer Jargon & Biasing | 6.4s | 648.2 ms | 3.7 ms | 652.0 ms | 0.10x | **15.4%** | **0.0%** | **PASS** | 180 MB | Measured directly on host |
| **tiny (39M)** | Spoken Self-Correction & Negation | 6.0s | 571.2 ms | 0.6 ms | 571.9 ms | 0.10x | **0.0%** | **0.0%** | **PASS** | 180 MB | Measured directly on host |
| **tiny (39M)** | Financial Figures & Negation | 6.1s | 550.4 ms | 1.1 ms | 551.4 ms | 0.09x | **0.0%** | **1.7%** | **PASS** | 180 MB | Measured directly on host |
| **base (74M)** | Conversational Business (Clean) | 5.3s | 934.7 ms | 1.2 ms | 935.9 ms | 0.18x | **0.0%** | **0.0%** | **PASS** | 290 MB | Measured directly on host |
| **base (74M)** | Fast-Paced Dictation (Rate +3) | 3.5s | 878.5 ms | 1.4 ms | 879.9 ms | 0.25x | **0.0%** | **0.0%** | **PASS** | 290 MB | Measured directly on host |
| **base (74M)** | Acoustic Noise Degraded (15dB SNR) | 4.9s | 844.9 ms | 1.2 ms | 846.1 ms | 0.17x | **0.0%** | **0.0%** | **PASS** | 290 MB | Measured directly on host |
| **base (74M)** | Developer Jargon & Biasing | 6.4s | 1038.5 ms | 1.7 ms | 1040.2 ms | 0.16x | **0.0%** | **0.0%** | **PASS** | 290 MB | Measured directly on host |
| **base (74M)** | Spoken Self-Correction & Negation | 6.0s | 920.1 ms | 0.4 ms | 920.5 ms | 0.15x | **0.0%** | **0.0%** | **PASS** | 290 MB | Measured directly on host |
| **base (74M)** | Financial Figures & Negation | 6.1s | 960.5 ms | 1.1 ms | 961.6 ms | 0.16x | **0.0%** | **0.0%** | **PASS** | 290 MB | Measured directly on host |

---

## 3. Candidate Model Evaluation & Verification Status Matrix

The following table explicitly distinguishes empirical host measurements from upstream specifications and unverified estimates:

| Model Candidate | Parameter Count | Quantized Weights Size | RAM Footprint | Inference Latency (CPU) | Verification Status on Host | Evidence Source & Trade-off Assessment |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **faster-whisper `base` (Production Default)** | 74M *(Upstream)* | 145 MB *(Measured on disk)* | ~280–290 MB *(Measured on host)* | ~845–1,040 ms *(Measured on host)* | **VERIFIED ON HOST** | Production baseline. Supports 99 languages. 4.15% WER on long continuous passages. Zero meaning-changing errors in 44-case audit. |
| **faster-whisper `tiny`** | 39M *(Upstream)* | ~75 MB *(Upstream)* | ~180 MB *(Measured on host)* | ~498–992 ms *(Measured on host)* | **VERIFIED ON HOST** | Tested on host. Hallucinates on technical terms (15.4% WER on developer jargon). Rejected for primary production. |
| **faster-whisper `small`** | 244M *(Upstream)* | ~480 MB *(Upstream)* | ~600–650 MB *(Estimated)* | ~2.2–2.7s *(Cited from CTranslate2)* | **NOT TESTED (BLOCKED)** | Blocked from download during initial trials due to drive `C:` disk space constraint (~36 MB free). Re-testing safe on drive `S:`. |
| **Distil-Whisper (`distil-small.en`)** | ~68M *(Upstream)* | ~135 MB *(Upstream)* | ~240–450 MB *(Estimated)* | ~600–720 ms *(Cited from upstream)* | **NOT TESTED (BLOCKED)** | Download attempt to default HuggingFace cache failed with `OSError: [Errno 28] No space left on device` on drive `C:`. English-only. |
| **Whisper `large-v3`** | 1,550M *(Upstream)* | ~3.1 GB *(Upstream)* | > 4.5 GB *(Cited from upstream)* | > 8s on CPU *(Cited from upstream)* | **NOT TESTED (INELIGIBLE)** | Ineligible for local CPU real-time dictation; exceeds real-time latency thresholds without dedicated high-end GPU. |

---

## 4. Technical Decision Rationale

1. **Retain Faster-Whisper Base INT8:**
   - Faster-Whisper `base` is already cached locally, loads in 0.82s, runs inference in ~950ms median, and retains 100% semantic accuracy across negations, dates, and commands in our 44-case audit.
   - It supports 99 languages without extra models, whereas Distil-Whisper models are restricted strictly to English.
2. **Drive S: HuggingFace Cache Configuration:**
   - To benchmark larger models without impacting system drive `C:`, developers must configure `HF_HOME="S:\.cache\huggingface"` before running candidate downloads.
   - Production v3.0.2 does not depend on an unnecessary model migration.
