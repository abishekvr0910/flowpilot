# Local SLM GGUF Benchmark Report (`Qwen2.5-0.5B-Instruct-Q4_K_M.gguf`)

- **Date (UTC):** `2026-10-27T00:59:47Z`
- **Branch:** `feature/local-slm-repair-sandbox`
- **Specification:** [`docs/specs/0004-local-text-repair-sandbox.md`](../specs/0004-local-text-repair-sandbox.md)
- **Harness:** [`scripts/benchmark_local_text_repair.py`](../../scripts/benchmark_local_text_repair.py)
- **Raw Artifact:** [`docs/evaluation/local_slm_gguf_benchmark_2026-10-27.json`](./local_slm_gguf_benchmark_2026-10-27.json)

---

## 1. Host & Model Provenance

| Parameter | Measured Value |
| :--- | :--- |
| **Host Node** | `LAPTOP-5KASE5RO` (`Windows 10`, Python `3.11.15`) |
| **CPU** | `Intel64 Family 6 Model 154 Stepping 3, GenuineIntel` (`16` logical threads; `n_threads=4` optimal for 0.5B) |
| **Inference Runtime** | `llama-cpp-python 0.3.36` (CPU wheel, `n_ctx=512`, `n_batch=256`, KV prefix warmup enabled) |
| **Model File** | `qwen2.5-0.5b-instruct-q4_k_m.gguf` (`Qwen2.5-0.5B-Instruct`, `Q4_K_M`) |
| **File Size** | `491,400,032` bytes (`~468.6 MB`) |
| **SHA-256 Digest** | `74A4DA8C9FDBCD15BD1F6D01D621410D31C6FC00986F5EB687824E7B93D7A9DB` |
| **Worker Cold-Start Warmup** | `1,330.85 ms` (includes model load + 1-shot system prompt KV cache warmup) |
| **Worker Process Peak RSS** | `614.53 MB` (initial ready RSS: `525.0 MB`) |

---

## 2. Phase A — 150-Case Adversarial FactGuard & Unbounded CPU Latency Audit

Phase A evaluates all 150 adversarial utterances (containing numbers, currencies, dates, critical negations, and `snake_case`/`camelCase`/`PascalCase` code identifiers) with a `3,000.0 ms` ceiling so every utterance completes CPU generation and exercises Tier 1 (`SlotLocker`), Tier 2 (`Llama` worker inference), and Tier 3 (`SlotLocker.restore` + `find_missing_slots` + `find_duplicated_slots` + `verify_critical_facts`).

### 2.1 Execution Status & FactGuard Efficacy (`N = 150`)

| Metric | Result | Target / Contract |
| :--- | :--- | :--- |
| **Total Adversarial Utterances** | `150` | `150` |
| **`REPAIRED` (Passed All 3 Tiers)** | **`135 / 150 (90.0%)`** | Clean disfluency removal & punctuation |
| **`VETOED_FACT_MISMATCH` (Caught by Tier 3)** | **`15 / 150 (10.0%)`** | Safe fallback to raw transcript on slot duplication/drop |
| **`FALLBACK_ERROR` / `FALLBACK_TIMEOUT`** | `0 / 150 (0.0%)` | Zero runtime crashes |
| **Post-Delivery Factual Leaks** | **`0 / 150 (0.0%)`** | **0.0% entity/negation/identifier loss or hallucination** |
| **Completed Within `<= 400.0 ms` on CPU** | **`0 / 150 (0.0%)`** | Strict interactive budget (`<= 400.0 ms`) |

### 2.2 CPU Inference Latency Distribution (`N = 150`)

| Cohort | Count | Min (ms) | P50 (ms) | Mean (ms) | P90 (ms) | P95 (ms) | Max (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **All Utterances** | `150` | `1,120.11` | `1,361.49` | `1,420.07` | `1,706.56` | `1,847.59` | `2,050.53` |
| **`REPAIRED` Only** | `135` | `1,120.11` | `1,348.04` | `1,399.81` | `1,667.10` | `1,865.30` | `2,050.53` |
| **`VETOED_FACT_MISMATCH` Only** | `15` | `1,440.08` | `1,616.68` | `1,602.38` | `1,720.42` | `1,748.65` | `1,837.59` |

### 2.3 Representative `REPAIRED` Outputs

1. **Input (`5` locked slots, `1,248.71 ms`):**
   - Raw: `"um we must not deploy commit 100 to production before 1 pm because check_status_code returned 400"`
   - Delivered: `"We must not deploy commit 100 to production before 1 pm because check_status_code returned 400."`
2. **Input (`4` locked slots, `1,242.11 ms`):**
   - Raw: `"the latency target is 152 ms at p50 and cannot exceed 400 ms under any circumstances in FlowOrchestrator"`
   - Delivered: `"The latency target is 152 ms at p50 and cannot exceed 400 ms under any circumstances in FlowOrchestrator."`
3. **Input (`4` locked slots, `1,410.53 ms`):**
   - Raw: `"um the discount rate is 8.0% for tier_2 customers so don't apply the £75.00 surcharge"`
   - Delivered: `"The discount rate is 8.0% for tier_2 customers so don't apply the £75.00 surcharge."`

### 2.4 Root Cause of the 15 `VETOED_FACT_MISMATCH` Cases

All 15 vetoed utterances came from template #5 (`"neither node_{a} nor node_{b} should accept port {port} when allow_external_access is false"`), which locks 6 slots (`<SLOT_0>` through `<SLOT_5>`). In Qwen2.5's BPE tokenizer, each `<SLOT_N>` placeholder splits into 5 subword tokens (`['<', 'SLOT', '_', 'N', '>']`), adding 30 placeholder subwords to the sentence. On that 6-slot template, `Qwen2.5-0.5B-Instruct` duplicated `<SLOT_3>` (the port number, e.g., `8004`). Tier 3 (`SlotLocker.find_duplicated_slots` + `verify_critical_facts`) detected the duplicate entity on 100% of those 15 occurrences (`FactGuard veto: missing=[], added=['8004']`) and returned the unmodified raw transcript, preserving **0% post-delivery factual error**.

---

## 3. Phase B — 25-Case Strict `400.0 ms` Production Deadline Enforcement

Phase B restores `LocalTextRepair.MAX_LATENCY_MS = 400.0` (the production non-blocking contract) and runs 25 consecutive adversarial utterances.

| Metric | Measured Result |
| :--- | :--- |
| **Sample Size** | `25` |
| **Hard Deadline (`MAX_LATENCY_MS`)** | `400.0 ms` |
| **`FALLBACK_TIMEOUT` (Worker Terminated)** | `1 / 25` (`474.47 ms` caller duration including OS process kill) |
| **`FALLBACK_UNPROVISIONED` (Cold-Start Guard)** | `24 / 25` (fast-path fallback while respawned worker loads GGUF) |
| **Caller Latency (`P50` / `P95` / `Max`)** | `61.81 ms` / `64.30 ms` / `474.47 ms` |
| **Post-Delivery Factual Leaks** | **`0 / 25 (0.0%)`** |

---

## 4. Architectural Conclusion & Release Gate Verdict

1. **Three-Tier Guard Protocol & Process Isolation Are Proven:**
   - Across 150 adversarial utterances (Phase A) and 25 strict-timeout stress cases (Phase B), **post-delivery factual leak rate is `0.0%` (`0 / 175`)**.
   - Hard process termination (`_terminate_worker_process`) and bounded cold-start fallback (`<= 50 ms` poll) prevent native C++ inference from stalling dictation when CPU latency exceeds `400.0 ms`.
2. **CPU Autoregressive Latency Exceeds the `400 ms` Interactive Budget:**
   - Because full-sentence autoregressive generation of 25–40 tokens (inflated by 5 BPE subwords per `<SLOT_N>` placeholder) takes `1,120–2,050 ms` (`P50 = 1,361.49 ms`) on a 4-thread CPU backend, **0% of multi-slot utterances finish within the `400.0 ms` budget on CPU**.
   - Furthermore, worker peak RSS (`614.53 MB`) slightly exceeds the `600 MB` RSS budget noted in Spec 0004 §3.2.
3. **Why `feature/local-slm-repair-sandbox` Remains Isolated from `master`:**
   - Merging full-sentence CPU GGUF generation into `master` would result in near-100% timeout fallbacks on CPU-only machines while consuming `~525–615 MB` of background RAM.
   - Before promoting Feature 30 from `feature/local-slm-repair-sandbox` to `master`, Tier 2 must either:
     1. Register single-token special tokens (`<SLOT_0>`..`<SLOT_9>`) or use span-level edit instructions so the model generates only diff tokens rather than regenerating the entire sentence, and/or
     2. Run on a hardware-accelerated backend (CUDA / Vulkan / NPU) capable of `>= 100 tokens/sec` (`<= 300 ms` P50).
