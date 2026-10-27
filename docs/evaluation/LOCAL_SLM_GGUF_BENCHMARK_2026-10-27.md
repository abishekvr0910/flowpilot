# Local SLM GGUF Benchmark Report (`Qwen2.5-0.5B-Instruct-Q4_K_M.gguf`)

- **Date (UTC):** `2026-10-27T01:49:33Z`
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
| **Inference Runtime** | `llama-cpp-python 0.3.36` (CPU wheel, `n_ctx=128`, `n_batch=64`, KV prefix warmup enabled) |
| **Model File** | `qwen2.5-0.5b-instruct-q4_k_m.gguf` (`Qwen2.5-0.5B-Instruct`, `Q4_K_M`) |
| **File Size** | `491,400,032` bytes (`~468.6 MiB`) |
| **SHA-256 Digest** | `74A4DA8C9FDBCD15BD1F6D01D621410D31C6FC00986F5EB687824E7B93D7A9DB` |
| **Worker Cold-Start Warmup** | `1,206.05 ms` (includes model load + 1-shot system prompt KV cache warmup) |
| **Worker Process RSS** | `513.9 MB` initial ready RSS / `610.70 MB` peak RSS after 175 inferences |

---

## 2. Architecture Comparison: Full-Sentence Regeneration vs. `SpanDiffEditor` (`span_diff`)

Instead of regenerating an entire 35-word sentence token-by-token on CPU (where each `<SLOT_N>` expands into 5 BPE subwords `['<', 'SLOT', '_', 'N', '>']`), [`SpanDiffEditor`](../../engine/local_text_repair.py) extracts the 3-word opening span, compresses `<SLOT_N>` into 2-token `@N` anchors, bounds SLM generation to `SPAN_MAX_TOKENS = 6`, strips isolated filler tokens (`um`, `uh`, `er`, `ah`) from the locked body tail, and splices the repaired span back onto the untouched slot-locked body before Tier-3 FactGuard verification.

| Metric | Baseline: Full-Sentence Regeneration | New: `SpanDiffEditor` (`span_diff`) | Improvement |
| :--- | :---: | :---: | :---: |
| **Phase A `REPAIRED` Rate (`N = 150`)** | `135 / 150 (90.0%)` | **`150 / 150 (100.0%)`** | **`+10.0%` (`0` slot drops/duplications)** |
| **Phase A `VETOED_FACT_MISMATCH`** | `15 / 150 (10.0%)` | **`0 / 150 (0.0%)`** | Eliminated 6-slot port duplication |
| **Phase A Completed `<= 400.0 ms`** | `0 / 150 (0.0%)` | **`149 / 150 (99.33%)`** | **`+99.33%` within strict CPU budget** |
| **Phase A CPU Latency `P50`** | `1,361.49 ms` | **`169.76 ms`** | **`8.02x` faster ($\le 300\text{ ms}$ target met)** |
| **Phase A CPU Latency `P90`** | `1,706.56 ms` | **`241.97 ms`** | **`7.05x` faster** |
| **Phase A CPU Latency `P95`** | `1,847.59 ms` | **`244.74 ms`** | **`7.55x` faster ($\le 400\text{ ms}$ deadline met)** |
| **Phase A CPU Latency `Mean`** | `1,420.07 ms` | **`180.46 ms`** | **`7.87x` faster** |
| **Phase B Strict `400 ms` `REPAIRED` (`N = 25`)** | `0 / 25 (0.0%)` | **`25 / 25 (100.0%)`** | **`100%` pass (`P50 = 160.58 ms`, `P95 = 225.67 ms`)** |
| **Post-Delivery Factual Leaks (`N = 175`)** | **`0 / 175 (0.0%)`** | **`0 / 175 (0.0%)`** | **100% FactGuard safety maintained** |

---

## 3. Detailed `SpanDiffEditor` Results (`2026-10-27T01:49:33Z`)

### 3.1 Phase A — 150-Case Adversarial Corpus (`ceiling = 3,000.0 ms`)

| Cohort | Count | Min (ms) | P50 (ms) | Mean (ms) | P90 (ms) | P95 (ms) | Max (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **All Utterances (`REPAIRED`)** | `150` | `114.13` | **`169.76`** | `180.46` | `241.97` | **`244.74`** | `455.85` |

### 3.2 Phase B — 25-Case Strict `400.0 ms` Production Deadline (`MAX_LATENCY_MS = 400.0 ms`)

| Metric | Measured Result |
| :--- | :--- |
| **Sample Size** | `25` |
| **Hard Deadline (`MAX_LATENCY_MS`)** | `400.0 ms` |
| **`REPAIRED` (Passed All 3 Tiers Under 400 ms)** | **`25 / 25 (100.0%)`** |
| **`FALLBACK_TIMEOUT` / `FALLBACK_UNPROVISIONED`** | `0 / 25 (0.0%)` |
| **Caller Latency (`Min` / `P50` / `P90` / `P95` / `Max`)** | `123.60 ms` / **`160.58 ms`** / `222.61 ms` / **`225.67 ms`** / `251.12 ms` |
| **Post-Delivery Factual Leaks** | **`0 / 25 (0.0%)`** |

### 3.3 Representative `SpanDiffEditor` Outputs

1. **Input (`5` locked slots, `134.28 ms`):**
   - Raw: `"um we must not deploy commit 100 to production before 1 pm because check_status_code returned 400"`
   - Delivered: `"We must not deploy commit 100 to production before 1 pm because check_status_code returned 400."`
2. **Input (`5` locked slots, `134.41 ms`):**
   - Raw: `"uh please do not charge more than $25.00 for invoice 5001 and never overwrite user_profile_id"`
   - Delivered: `"Please do not charge more than $25.00 for invoice 5001 and never overwrite user_profile_id."`
3. **Input (`6` locked slots, `242.33 ms`):**
   - Raw: `"neither node_5 nor node_6 should accept port 8004 when allow_external_access is false"`
   - Delivered: `"Neither node_5 nor node_6 should accept port 8004 when allow_external_access is false."`
4. **Input (`4` locked slots, `128.32 ms`):**
   - Raw: `"um the discount rate is 8.0% for tier_2 customers so don't apply the £75.00 surcharge"`
   - Delivered: `"The discount rate is 8.0% for tier_2 customers so don't apply the £75.00 surcharge."`

---

## 4. Remaining Constraints & Why `feature/local-slm-repair-sandbox` Stays Sandboxed During RC9 Pilot

1. **Latency & Factual Safety Solved:** `SpanDiffEditor` brings CPU P50 latency down to **`169.76 ms`** (`P95 = 244.74 ms`, `99.33% <= 400 ms`, `25/25` passing in strict 400 ms Phase B) with **`150/150 (100.0%)` `REPAIRED`** and **`0%` factual leaks**.
2. **Worker Memory Footprint (`513.9 MB` initial / `610.70 MB` peak RSS):** Because `Qwen2.5-0.5B-Instruct-Q4_K_M.gguf` is `491.4 MB` on disk, the isolated worker process still consumes `~514–611 MB` of resident memory (`+10.7 MB` above the `600 MB` budget at peak).
3. **Scope of `SpanDiffEditor`:** The 3-word opening span + tail filler stripping handles leading disfluencies, capitalization, terminal punctuation, and isolated inline fillers (`um`, `uh`, `er`, `ah`), while mid-sentence grammatical restructuring remains bounded by design so slots in the body cannot be reordered or dropped.
4. **Release Policy:** Per Spec 0004 §1.1.4, `feature/local-slm-repair-sandbox` remains decoupled from `master` while `v3.1.0-RC9` completes pilot validation.
