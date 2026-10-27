# Local SLM GGUF Benchmark Report (`Qwen2.5-0.5B-Instruct-Q4_K_M.gguf`)

- **Date (UTC):** `2026-10-27T02:10:23Z`
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
| **Inference Runtime** | `llama-cpp-python 0.3.36` (CPU wheel, `n_ctx=256`, `n_batch=128`, `use_mmap=True`, `logits_all=False`, KV prefix warmup + post-call `gc.collect()`) |
| **Model File** | `qwen2.5-0.5b-instruct-q4_k_m.gguf` (`Qwen2.5-0.5B-Instruct`, `Q4_K_M`) |
| **File Size** | `491,400,032` bytes (`~468.6 MiB`) |
| **SHA-256 Digest** | `74A4DA8C9FDBCD15BD1F6D01D621410D31C6FC00986F5EB687824E7B93D7A9DB` |
| **Worker Process RSS** | **`516.20 MB` initial ready RSS / `519.62 MB` peak RSS** across 206 total inferences (`80.38 MB` below the `600 MB` budget) |

---

## 2. Phase 0 — Cold-Start & Worker Memory Audit

Measures first-call behavior when `LocalTextRepair.repair()` is invoked cold before the worker process has finished loading GGUF weights:

| Cold-Start Metric | Measured Value | Contract / Target |
| :--- | :--- | :--- |
| **Unwarmed First-Call Status** | `FALLBACK_UNPROVISIONED` (`fallback_used=True`) | Immediate raw fallback without blocking dictation |
| **Unwarmed First-Call Caller Latency** | **`86.17 ms`** | Bounded fast-fail ($\le 100\text{ ms}$ including `spawn` init) |
| **Background Worker Cold Ready Time** | **`1,498.04 ms`** | Full GGUF load + 1-shot KV prefix warmup |
| **First Warm Call Status & Latency** | **`REPAIRED` in `131.64 ms`** | $\le 300\text{ ms}$ warm target |
| **Worker Initial / Peak RSS (206 calls)** | **`516.20 MB` / `519.62 MB`** | **$\le 600.0\text{ MB}$ (`-80.38 MB` headroom)** |

> **Root cause of previous `610.70 MB` RSS peak resolved:** `llama-cpp-python` allocates a `LlamaSampler` and ctypes buffer per call. Running `gc.collect()` in the worker loop immediately *after* sending the pipe response reclaims those per-call buffers off the critical path, keeping worker RSS flat at `516.20–519.62 MB` across all 206 inferences.

---

## 3. Evolution Across Three Sandbox Iterations

| Metric | Iteration 1: Full-Sentence Regeneration (`770c7bc`) | Iteration 2: Initial `SpanDiffEditor` (`dbe9b7d`) | Iteration 3: Hardened `SpanDiffEditor` + Gold & Edge Guards |
| :--- | :---: | :---: | :---: |
| **Phase A Guard-Pass (`REPAIRED`)** | `135 / 150 (90.0%)` | `150 / 150 (100.0%)` | **`150 / 150 (100.0%)`** |
| **Phase A Gold Exact Match** | Not measured | Not measured | **`150 / 150 (100.0%)`** |
| **Phase B 30-Case Edge-Case Gold Match** | N/A | `24 / 30 (80.0%)` (before `do`/`can` fix) | **`30 / 30 (100.0%)`** |
| **Phase C Strict `400 ms` Gold Match** | `0 / 25 (0.0%)` | `25 / 25 (100.0%)` | **`25 / 25 (100.0%)`** |
| **Phase A CPU Latency `P50`** | `1,361.49 ms` | `169.76 ms` | **`170.71 ms`** |
| **Phase A CPU Latency `P95`** | `1,847.59 ms` | `244.74 ms` | **`253.96 ms`** |
| **Phase B Edge-Case Latency `P50` / `P95`** | N/A | N/A | **`137.69 ms` / `218.37 ms` (`Max = 243.79 ms`)** |
| **Phase C Strict `400 ms` `P50` / `P95`** | `61.81 ms` (fallback) | `160.58 ms` / `225.67 ms` | **`184.61 ms` / `242.65 ms` (`Max = 273.61 ms`)** |
| **Worker Process Peak RSS** | `614.53 MB` | `610.70 MB` | **`519.62 MB` ($\le 600\text{ MB}$ PASS)** |
| **Post-Delivery Factual Leaks** | **`0 / 175 (0.0%)`** | **`0 / 175 (0.0%)`** | **`0 / 205 (0.0%)`** |

---

## 4. Phase B — 30-Case Hard Semantic & Edge-Case Gold Suite (`100.0%` Gold Match)

Evaluates 10 categories (3 variations each = 30 cases) under the strict `400.0 ms` deadline (`P50 = 137.69 ms`, `P95 = 218.37 ms`, `Max = 243.79 ms`, **`30 / 30 (100.0%)` Gold Exact Match**):

| Category | Raw Input Sample | Expected Gold & Delivered Output (`100%` Match) | Latency |
| :--- | :--- | :--- | :---: |
| **`natural_at_n_tail`** | `"um please ping @0 and @1 before 1 pm so check_user_handle does not fail"` | `"Please ping @0 and @1 before 1 pm so check_user_handle does not fail."` | `135.84 ms` |
| **`natural_at_n_head`** | `"@0 and @1 must not accept port 2021 when allow_external_access is false"` | `"@0 and @1 must not accept port 2021 when allow_external_access is false."` | `218.37 ms` |
| **`literal_slot_token`** | `"uh do not replace <SLOT_0> or @99 when testing SlotLocker with 3 inputs"` | `"Do not replace <SLOT_0> or @99 when testing SlotLocker with 3 inputs."` | `171.61 ms` |
| **`filler_in_meaning_subject`** | `"um is a common filler word that should not break parse_token_stream in 2023"` | `"Um is a common filler word that should not break parse_token_stream in 2023."` | `216.82 ms` |
| **`filler_in_meaning_meta_mention`** | `"uh please do not delete the word um or the token uh when running suite 5"` | `"Please do not delete the word um or the token uh when running suite 5."` | `120.71 ms` |
| **`filler_in_meaning_quoted`** | `"um we should not strip 'um' or \"uh\" from raw_transcript_buffer during 6 runs"` | `"We should not strip 'um' or \"uh\" from raw_transcript_buffer during 6 runs."` | `139.54 ms` |
| **`acronym_and_unit_homographs`** | `"uh the patient in ER room 7 must not wait um more than 15 minutes for a 50 Ah battery"` | `"The patient in ER room 7 must not wait more than 15 minutes for a 50 Ah battery."` | `124.56 ms` |
| **`interrogative_why`** | `"um why did check_status_code return 2027 instead of 200 when retry_limit_enabled was not set"` | `"Why did check_status_code return 2027 instead of 200 when retry_limit_enabled was not set?"` | `132.36 ms` |
| **`interrogative_can`** | `"uh can we deploy commit 2028 before 9 pm without breaking user_session_id"` | `"Can we deploy commit 2028 before 9 pm without breaking user_session_id?"` | `104.21 ms` |
| **`inline_tail_fillers`** | `"the service did not crash um after 1 hours uh in AudioRecorder during stress_test_run"` | `"The service did not crash after 1 hours in AudioRecorder during stress_test_run."` | `169.23 ms` |
