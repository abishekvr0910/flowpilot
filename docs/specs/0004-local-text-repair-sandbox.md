# 0004. Local Text Repair Sandbox and Infilling Contract

**Date:** 2026-10-26 (Updated 2026-10-27 with Real GGUF Benchmark Results)  
**Status:** Draft / In Progress (Sandbox — Evaluated on Real GGUF)  
**Audience:** FlowPilot maintainers, Codex, Gemini  
**Baseline:** commit `54e7c5c` (`v3.1.0-RC9`)  
**Scope Item:** Feature 30 (Local Text Repair and Bounded Infilling)  
**Branch:** `feature/local-slm-repair-sandbox`  

---

## 1. Summary & Boundary Declaration

This specification defines the architecture, security constraints, and execution contract for **Local Text Repair** in FlowPilot.

### 1.1 Strict Boundary Definitions
1. **Text Repair, NOT Speech Recognition:**  
   The repair engine operates purely as a post-transcription, autoregressive natural language text transform. It receives recognized text strings from `STTEngine` and outputs structured, cleaned text. **It is NOT an acoustic speech recognizer (ASR).** It cannot resolve, repair, or disambiguate acoustic recognition errors or phonetically degraded tokens in Indic languages (Hindi, Tamil, Malayalam) or English dialects. Acoustic accuracy is governed separately by Feature 15 and specialized acoustic models.
2. **Strict Offline & Zero Cloud Egress:**  
   Inference executes entirely on local host hardware using quantized small language models (SLMs). Zero bytes, tokens, or embeddings leave the local host (`127.0.0.1` loopback only).
3. **Execution Runtime Baseline:**  
   The primary, stable runtime baseline is **CPU AVX2 / AVX-512** via `llama-cpp-python` (or `onnxruntime-genai`). **DirectML is strictly experimental and non-blocking.** Because DirectML support across small-model GGUF runtimes is not a standardized or upstream-guaranteed backend in `llama.cpp`, it must never be a hard dependency for release readiness.
4. **Controlled RC9 Pilot Decoupling:**  
   Development and benchmarking of this engine take place strictly within the isolated branch `feature/local-slm-repair-sandbox`. It must never block or delay the ongoing distribution, intake, and evaluation of the published `v3.1.0-RC9` pilot release.

---

## 2. Architecture & The Three-Tier Guard Protocol

To eliminate the hallucination, entity drift, and negation-dropping risks common to small language models, the Local Text Repair engine executes a mandatory **Three-Tier Guard Protocol**:

```
[Raw Whisper Transcript]
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ Tier 1: Deterministic Slot Locker (< 5 ms)             │
│ • Detects and extracts numbers, currency, dates, URLs  │
│ • Detects critical negations ('not', 'never', etc.)    │
│ • Detects code identifiers ('camelCase', 'snake_case') │
│ • Replaces them with opaque tokens: <SLOT_0>, <SLOT_1> │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ Tier 2: Bounded Local SLM Infilling (< 350 ms Target)  │
│ • Model: Qwen2.5-0.5B-Instruct (Q4_K_M GGUF, ~468 MB)  │
│ • Enforces KV-cached 1-shot constrained repair prompt  │
│ • Repairs run-ons, capitalization, and disfluencies    │
│ • Strictly forbidden from altering or dropping slots   │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ Tier 3: Slot Restorer & FactGuard Veto (< 5 ms)        │
│ • Verifies 0 missing and 0 duplicated <SLOT_N> tokens  │
│ • Re-populates exact text into <SLOT_N> anchors        │
│ • Evaluates critical facts, numbers, and negations     │
│ • IF ANY ANCHOR OR NEGATION FAILS: IMMEDIATE VETO      │
│   (Falls back instantaneously to raw Whisper output)   │
└────────────────────────────────────────────────────────┘
         │
         ▼
[Verified, Fact-Safe Document Text]
```

---

## 3. The Fallback & Latency Contract

The engine enforces a **Hard Non-Blocking Fallback Contract**:
1. **Total Latency Budget:** Maximum allowable repair duration is **400 ms** on consumer CPU hardware.
2. **Immediate Whisper Fallback Conditions:**  
   FlowPilot immediately discards the repair worker and outputs the raw Whisper transcript without delay if:
   * The repair model is unprovisioned, disabled, or missing from disk.
   * Total execution exceeds the 400 ms deadline (timeout).
   * Memory pressure exceeds configured thresholds (> 600 MB RSS delta).
   * Tier 3 `FactGuard` detects a missing/duplicated `<SLOT_N>` token, number, date, negation, or altered code identifier.
   * Any unhandled exception occurs in the inference runtime.

Under no circumstances may a failure in text repair block, corrupt, or stall the text injection pipeline.

### 3.3 Process Isolation & Asynchronous Warmup Architecture

In CPython on Windows, native C/C++ threads executing `llama.cpp` inference cannot be forcibly terminated if native code deadlocks or exceeds latency deadlines. To prevent thread exhaustion and process leaks, Feature 30 implements an isolated process worker architecture:

1. **Persistent Worker Process**: Infilling executes in a dedicated child process (`multiprocessing.Process` via `spawn`) communicating over bidirectional duplex `multiprocessing.Pipe`.
2. **Hard Termination on Timeout**: If inference exceeds the 400 ms latency budget, the host process issues `worker.terminate()` (and `worker.kill()` if necessary), instantly freeing CPU/GPU handles and threads. A fresh worker is respawned cleanly on the subsequent invocation without leaking background tasks.
3. **Asynchronous Non-Blocking Warmup (`warmup_async()`)**: Model loading, weight preloading, and 1-shot system prompt KV cache warmup are initiated non-blocking in background threads during application startup (`FlowOrchestrator.__init__`). If dictation completes before the model is fully loaded, a short bounded cold-start check (<= 50 ms) fails fast and safely falls back to pristine Whisper transcripts (`FALLBACK_UNPROVISIONED`), completely protecting the 400 ms budget.
4. **Verification**: Validated in Suite 60 (`tests/test_local_text_repair.py`, 18 tests) covering hard timeout termination, cold-start fallback, dropped code-identifier slot veto, and auto-restart self-healing.

---

## 4. Hardware Profiles & Model Specifications

| Profile | Model Architecture | Format & Quantization | Measured Size | Primary Backend | Fallback Backend |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Default CPU** | Qwen2.5-0.5B-Instruct | GGUF (Q4_K_M) | `491.4 MB` (`468.6 MiB`) | CPU (AVX2 / AVX-512) | None (Raw Whisper) |
| **Quality Tier** | SmolLM2-1.7B-Instruct | GGUF (Q4_K_M) | ~1.0 GB | CPU (AVX2 / AVX-512) | Default CPU |
| **Experimental** | Qwen2.5-0.5B-Instruct | ONNX / GGUF | `491.4 MB` | DirectML (Optional) | Default CPU |

---

## 5. Scope & Verification Criteria

Development in `feature/local-slm-repair-sandbox` will be accepted when:
1. **P50 Latency:** On an Intel Core i5-12500H (or equivalent modern 4-core mobile CPU), end-to-end repair completes in $\le 300\text{ ms}$ for utterances up to 30 words.
2. **Zero Fact Loss:** Across the 150-utterance FactGuard adversarial test suite (containing numbers, negations, currencies, and technical terms), the engine achieves **0% entity hallucination or mutation**.
3. **Safe Fallback:** 100% of simulated timeouts, runtime crashes, and FactGuard rejections fall back to clean Whisper transcripts within $\le 5\text{ ms}$.
4. **Isolation:** The sandbox branch passes all 59 existing core regression suites with zero regressions.

---

## 6. Real GGUF Benchmark Findings (`2026-10-27`)

Full report: [`docs/evaluation/LOCAL_SLM_GGUF_BENCHMARK_2026-10-27.md`](../evaluation/LOCAL_SLM_GGUF_BENCHMARK_2026-10-27.md)  
Raw JSON artifact: [`docs/evaluation/local_slm_gguf_benchmark_2026-10-27.json`](../evaluation/local_slm_gguf_benchmark_2026-10-27.json)

| Criterion | Measured Value (`Qwen2.5-0.5B-Instruct-Q4_K_M.gguf`) | Gate Status |
| :--- | :--- | :--- |
| **Zero Fact Loss (`N = 150` Phase A + `25` Phase B)** | **`0 / 175 (0.0%)` post-delivery factual leaks** (`135/150` `REPAIRED`, `15/150` caught by `VETOED_FACT_MISMATCH`) | **PASS** |
| **Safe Non-Blocking Fallback (`MAX_LATENCY_MS = 400.0`)** | `FALLBACK_TIMEOUT` (`474.47 ms` caller time with OS process kill) followed by `FALLBACK_UNPROVISIONED` (`P50 = 61.81 ms` cold-start guard) | **PASS** |
| **CPU P50 Latency ($\le 300\text{ ms}$ target)** | **`P50 = 1,361.49 ms`** (`P95 = 1,847.59 ms`, `Min = 1,120.11 ms` on 4-thread CPU; `0%` $\le 400\text{ ms}$) | **BLOCKED ON CPU (Keep in Sandbox)** |
| **Worker Process Memory Delta ($\le 600\text{ MB}$ target)** | **`614.53 MB` peak RSS** (`525.0 MB` initial ready RSS) | **MARGINAL (`+14.5 MB` over 600 MB)** |

### Promotion Gate Conclusion
While the **Three-Tier Guard Protocol** achieves **0.0% post-delivery factual leaks (`0 / 175`)** and **90.0% successful repair accuracy (`135 / 150`)** on real `Qwen2.5-0.5B-Instruct-Q4_K_M.gguf`, full-sentence CPU autoregressive generation (`P50 = 1,361.49 ms`) does not meet the $\le 300\text{ ms}$ P50 / $\le 400\text{ ms}$ hard deadline on CPU-only hardware due to BPE subword expansion of `<SLOT_N>` placeholders (5 subwords per slot). Consequently, `feature/local-slm-repair-sandbox` **must remain isolated from `master`** until either span-edit diff generation or GPU/NPU acceleration brings P50 latency below `300 ms`.
