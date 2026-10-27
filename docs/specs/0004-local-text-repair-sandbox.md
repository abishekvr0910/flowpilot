# 0004. Local Text Repair Sandbox and Infilling Contract

**Date:** 2026-10-26 (Updated 2026-10-27 with Hardened `SpanDiffEditor`, Gold-Output & Edge-Case Audit)  
**Status:** Evaluated in Sandbox (`feature/local-slm-repair-sandbox`)  
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

To eliminate the hallucination, entity drift, negation-dropping, and CPU latency overhead of full-sentence regeneration, the Local Text Repair engine executes a mandatory **Three-Tier Guard Protocol with Bounded Span-Diff Editing (`SpanDiffEditor`)**:

```
[Raw Whisper Transcript]
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ Tier 1: Deterministic Slot Locker (< 5 ms)             │
│ • Locks literal @N / <SLOT_N> tokens in user input     │
│ • Locks filler-in-meaning (subject, meta, quoted)      │
│ • Locks code identifiers, numbers, currency, dates     │
│ • Locks critical negations ('not', 'never', etc.)      │
│ • Replaces them with opaque tokens: <SLOT_0>, <SLOT_1> │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ Tier 2: SpanDiffEditor & Bounded SLM Infilling         │
│ • Extracts 3-word opening span; encodes slots as @N    │
│ • Model: Qwen2.5-0.5B-Instruct (Q4_K_M GGUF, ~468 MiB) │
│ • Bounds generation to <= 6 tokens (P50 ~170 ms CPU)   │
│ • Verifies non-filler content word conservation        │
│ • Splices repaired span onto slot-locked body tail     │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ Tier 3: Slot Restorer & FactGuard Veto (< 5 ms)        │
│ • Verifies 0 missing and 0 duplicated <SLOT_N> tokens  │
│ • Single-pass regex restoration (no double-expansion)  │
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
3. **Asynchronous Non-Blocking Warmup (`warmup_async()`) & Post-Call GC**: Model loading, weight preloading, and 1-shot system prompt KV cache warmup are initiated non-blocking in background threads during application startup (`FlowOrchestrator.__init__`). After sending each inference response over the pipe, the worker runs `gc.collect()` off the critical path, keeping worker RSS flat at `516.20–519.62 MB` across hundreds of calls.
4. **Verification**: Validated in Suite 60 (`tests/test_local_text_repair.py`, 23 tests) covering `SpanDiffEditor`, natural `@N` and `<SLOT_N>` collision guards, filler-in-meaning preservation, interrogative punctuation, hard timeout termination, cold-start fallback, dropped code-identifier slot veto, and auto-restart self-healing.

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
2. **Zero Fact Loss & Gold-Output Quality:** Across the 150-utterance FactGuard adversarial test suite and the 30-case Edge-Case Gold Suite (natural `@N`, filler-in-meaning, acronyms, questions), the engine achieves **0% entity hallucination or mutation** and verified gold-output exact match.
3. **Safe Fallback & Cold-Start Safety:** 100% of simulated timeouts, runtime crashes, unwarmed cold-start calls, and FactGuard rejections fall back to clean Whisper transcripts without blocking dictation.
4. **Memory & Regression Isolation:** Worker peak RSS stays $\le 600\text{ MB}$ (`519.62 MB` measured), and the sandbox branch passes all regression suites with zero regressions.

---

## 6. Real GGUF Benchmark Findings (`2026-10-27` — Hardened `SpanDiffEditor`)

Full report: [`docs/evaluation/LOCAL_SLM_GGUF_BENCHMARK_2026-10-27.md`](../evaluation/LOCAL_SLM_GGUF_BENCHMARK_2026-10-27.md)  
Raw JSON artifact: [`docs/evaluation/local_slm_gguf_benchmark_2026-10-27.json`](../evaluation/local_slm_gguf_benchmark_2026-10-27.json)

| Criterion | Measured Value (`Qwen2.5-0.5B-Instruct-Q4_K_M.gguf`) | Gate Status |
| :--- | :--- | :--- |
| **Cold-Start Unwarmed Call & Ready Time (Phase 0)** | `FALLBACK_UNPROVISIONED` in **`86.17 ms`**; ready in `1,498.04 ms`; first warm call `REPAIRED` in **`131.64 ms`** | **PASS** |
| **Worker Process Memory RSS ($\le 600\text{ MB}$ target)** | **`516.20 MB` initial / `519.62 MB` peak RSS** across 206 calls (`-80.38 MB` below limit) | **PASS** |
| **Phase A 150-Case Adversarial Gold Exact Match** | **`150 / 150 (100.0%)` Gold Exact Match**, **`0 / 150` fact leaks**, `P50 = 170.71 ms`, `P95 = 253.96 ms` | **PASS** |
| **Phase B 30-Case Edge-Case Gold Suite ($\le 400\text{ ms}$)** | **`30 / 30 (100.0%)` Gold Exact Match**, **`0 / 30` fact leaks**, `P50 = 137.69 ms`, `P95 = 218.37 ms`, `Max = 243.79 ms` | **PASS** |
| **Phase C 25-Case Strict `400 ms` Deadline** | **`25 / 25 (100.0%)` Gold Exact Match**, **`0 / 25` fact leaks**, `P50 = 184.61 ms`, `P95 = 242.65 ms`, `Max = 273.61 ms` | **PASS** |
