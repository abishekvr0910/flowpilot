# Local SLM GGUF Benchmark Report (`Qwen2.5-0.5B-Instruct-Q4_K_M.gguf`)

- **Date (UTC):** `2026-10-27T02:34:26Z`
- **Branch:** `feature/local-slm-repair-sandbox`
- **Specification:** [`docs/specs/0004-local-text-repair-sandbox.md`](../specs/0004-local-text-repair-sandbox.md)
- **Harness:** [`scripts/benchmark_local_text_repair.py`](../../scripts/benchmark_local_text_repair.py)
- **Raw Artifact:** [`docs/evaluation/LOCAL_SLM_GGUF_BENCHMARK_2026-10-27.json`](./LOCAL_SLM_GGUF_BENCHMARK_2026-10-27.json)

---

## 1. Host & Model Provenance

| Parameter | Measured Value |
| :--- | :--- |
| **Host Node** | `LAPTOP-5KASE5RO` (`Windows 10`, Python `3.11.15`) |
| **CPU** | `Intel64 Family 6 Model 154 Stepping 3, GenuineIntel` (`16` logical threads; `n_threads=4` optimal for 0.5B) |
| **Inference Runtime** | `llama-cpp-python 0.3.36` (CPU wheel, `n_ctx=256`, `n_batch=128`, `use_mmap=True`, `logits_all=False`, KV prefix warmup, `gc.collect(0)`, `ABOVE_NORMAL_PRIORITY_CLASS`) |
| **Model File** | `qwen2.5-0.5b-instruct-q4_k_m.gguf` (`Qwen2.5-0.5B-Instruct`, `Q4_K_M`) |
| **File Size** | `491,400,032` bytes (`~468.6 MiB`) |
| **SHA-256 Digest** | `74A4DA8C9FDBCD15BD1F6D01D621410D31C6FC00986F5EB687824E7B93D7A9DB` |
| **Worker Process RSS** | **`515.92 MB` initial ready RSS / `528.04 MB` peak RSS** across 226 total inferences (`71.96 MB` below the `600 MB` budget) |

---

## 2. Root-Cause Analysis & Resolution of the `404.30 ms` Phase A Outlier

In Iteration 3 (`315be23`), `149 / 150 (99.33%)` of Phase A cases completed within `<= 400.0 ms`, with a single outlier at `404.30 ms` (`+4.30 ms` above budget). Profiling identified three compounding causes:

1. **Multi-Slot 3-Word Opening Spans Without Leading Fillers (`"@4 @0 @5"`):**
   - Utterances without leading disfluencies (`"neither node_5 nor..."` $\rightarrow$ `"<SLOT_4> <SLOT_0> <SLOT_5>"`) extracted 3 compact slots (`"@4 @0 @5"` = `6` BPE tokens) even though only sentence-initial capitalization (`2` words, `"@4 @0"`) was needed.
   - **Fix:** `SpanDiffEditor.extract_span()` now uses an adaptive window (`3` words when a leading filler `um`/`uh` is present, `2` words otherwise), and `SpanDiffEditor.estimate_max_tokens()` dynamically bounds completion tokens (`2` to `6` tokens) based on the exact content and `@N` count of the extracted span.
2. **Unconditional Full 3-Generation `gc.collect()` After Every Request:**
   - Calling full `gc.collect()` after every single pipe response occasionally triggered a full generation-2 heap scan right before the next request arrived.
   - **Fix:** Replaced unconditional full `gc.collect()` with fast generation-0 `gc.collect(0)` on every call and a full `gc.collect()` only every 25 calls.
3. **Windows Thread Scheduling Preemption & Short-Sentence Threshold (`SPAN_THRESHOLD_WORDS`):**
   - Set `psutil.Process(os.getpid()).nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)` in `_slm_process_worker_entry` so Windows does not preempt the 4 `llama.cpp` threads onto efficiency cores, and lowered `SPAN_THRESHOLD_WORDS` from `8` to `2` so 3–8 word real-speech utterances also use bounded span-diff editing instead of full-sentence regeneration.

**Result:** Phase A `P50` dropped from `170.71 ms` to **`117.45 ms`**, `P95` dropped from `253.96 ms` to **`186.66 ms`**, `Max` dropped from `404.30 ms` to **`289.91 ms`**, and **`150 / 150 (100.0%)`** of Phase A cases completed well under `400.0 ms`.

---

## 3. Phase 0 — Cold-Start & Worker Memory Audit

Measures first-call behavior when `LocalTextRepair.repair()` is invoked cold before the worker process has finished loading GGUF weights:

| Cold-Start Metric | Measured Value | Contract / Target |
| :--- | :--- | :--- |
| **Unwarmed First-Call Status** | `FALLBACK_UNPROVISIONED` (`fallback_used=True`) | Immediate raw fallback without blocking dictation |
| **Unwarmed First-Call Caller Latency** | **`83.80 ms`** | Bounded fast-fail ($\le 100\text{ ms}$ including `spawn` init) |
| **Background Worker Cold Ready Time** | **`1,124.74 ms`** | Full GGUF load + 1-shot KV prefix warmup |
| **First Warm Call Status & Latency** | **`REPAIRED` in `109.40 ms`** | $\le 300\text{ ms}$ warm target |
| **Worker Initial / Peak RSS (226 calls)** | **`515.92 MB` / `528.04 MB`** | **$\le 600.0\text{ MB}$ (`-71.96 MB` headroom)** |

---

## 4. Evolution Across Four Sandbox Iterations

| Metric | Iteration 1: Full-Sentence (`770c7bc`) | Iteration 2: Initial `SpanDiffEditor` (`dbe9b7d`) | Iteration 3: Gold & Edge Guards (`315be23`) | Iteration 4: Adaptive Span + Real Speech |
| :--- | :---: | :---: | :---: | :---: |
| **Phase A Completed $\le 400\text{ ms}$** | `0 / 150 (0.0%)` | `149 / 150 (99.33%)` | `149 / 150 (99.33%)` | **`150 / 150 (100.0%)`** |
| **Phase A Guard-Pass (`REPAIRED`)** | `135 / 150 (90.0%)` | `150 / 150 (100.0%)` | `150 / 150 (100.0%)` | **`150 / 150 (100.0%)`** |
| **Phase A Gold Exact Match** | Not measured | Not measured | `150 / 150 (100.0%)` | **`150 / 150 (100.0%)`** |
| **Phase B 30-Case Edge-Case Gold Match** | N/A | `24 / 30 (80.0%)` | `30 / 30 (100.0%)` | **`30 / 30 (100.0%)`** |
| **Phase C Strict `400 ms` Gold Match** | `0 / 25 (0.0%)` | `25 / 25 (100.0%)` | `25 / 25 (100.0%)` | **`25 / 25 (100.0%)`** |
| **Phase D1 Real Human Speech (`Common Voice 17.0`)** | N/A | N/A | N/A | **`10 / 10 (100.0%)` $\le 400\text{ ms}$ (`0` WER loss)** |
| **Phase D2 Acoustic SAPI Disfluent Speech** | N/A | N/A | N/A | **`10 / 10 (100.0%)` $\le 400\text{ ms}$** |
| **Phase A CPU Latency `P50`** | `1,361.49 ms` | `169.76 ms` | `170.71 ms` | **`117.45 ms`** |
| **Phase A CPU Latency `P95`** | `1,847.59 ms` | `244.74 ms` | `253.96 ms` | **`186.66 ms`** |
| **Phase A CPU Latency `Max`** | `2,331.49 ms` | `455.85 ms` | `404.30 ms` | **`289.91 ms` ($\le 400\text{ ms}$ PASS)** |
| **Phase B Edge-Case Latency `P50` / `P95` / `Max`** | N/A | N/A | `137.69` / `218.37` / `243.79 ms` | **`139.55` / `213.97` / `280.98 ms`** |
| **Phase C Strict `400 ms` `P50` / `P95` / `Max`** | `61.81 ms` (timeout) | `160.58` / `225.67` / `257.41 ms` | `184.61` / `242.65` / `273.61 ms` | **`116.61` / `167.44` / `181.71 ms`** |
| **Worker Process Peak RSS** | `614.53 MB` | `610.70 MB` | `519.62 MB` | **`528.04 MB` ($\le 600\text{ MB}$ PASS)** |
| **Post-Delivery Factual Leaks** | **`0 / 175 (0.0%)`** | **`0 / 175 (0.0%)`** | **`0 / 205 (0.0%)`** | **`0 / 225 (0.0%)`** |

---

## 5. Phase B — 30-Case Hard Semantic & Edge-Case Gold Suite (`100.0%` Gold Match)

Evaluates 10 categories (3 variations each = 30 cases) under the strict `400.0 ms` deadline (`P50 = 139.55 ms`, `P95 = 213.97 ms`, `Max = 280.98 ms`, **`30 / 30 (100.0%)` Gold Exact Match**):

| Category | Raw Input Sample | Expected Gold & Delivered Output (`100%` Match) | Latency |
| :--- | :--- | :--- | :---: |
| **`natural_at_n_tail`** | `"um please ping @0 and @1 before 1 pm so check_user_handle does not fail"` | `"Please ping @0 and @1 before 1 pm so check_user_handle does not fail."` | `157.50 ms` |
| **`natural_at_n_head`** | `"@0 and @1 must not accept port 2021 when allow_external_access is false"` | `"@0 and @1 must not accept port 2021 when allow_external_access is false."` | `213.97 ms` |
| **`literal_slot_token`** | `"uh do not replace <SLOT_0> or @99 when testing SlotLocker with 3 inputs"` | `"Do not replace <SLOT_0> or @99 when testing SlotLocker with 3 inputs."` | `280.98 ms` |
| **`filler_in_meaning_subject`** | `"um is a common filler word that should not break parse_token_stream in 2023"` | `"Um is a common filler word that should not break parse_token_stream in 2023."` | `233.34 ms` |
| **`filler_in_meaning_meta_mention`** | `"uh please do not delete the word um or the token uh when running suite 5"` | `"Please do not delete the word um or the token uh when running suite 5."` | `169.62 ms` |
| **`filler_in_meaning_quoted`** | `"um we should not strip 'um' or \"uh\" from raw_transcript_buffer during 6 runs"` | `"We should not strip 'um' or \"uh\" from raw_transcript_buffer during 6 runs."` | `183.01 ms` |
| **`acronym_and_unit_homographs`** | `"uh the patient in ER room 7 must not wait um more than 15 minutes for a 50 Ah battery"` | `"The patient in ER room 7 must not wait more than 15 minutes for a 50 Ah battery."` | `160.62 ms` |
| **`interrogative_why`** | `"um why did check_status_code return 2027 instead of 200 when retry_limit_enabled was not set"` | `"Why did check_status_code return 2027 instead of 200 when retry_limit_enabled was not set?"` | `142.14 ms` |
| **`interrogative_can`** | `"uh can we deploy commit 2028 before 9 pm without breaking user_session_id"` | `"Can we deploy commit 2028 before 9 pm without breaking user_session_id?"` | `116.86 ms` |
| **`inline_tail_fillers`** | `"the service did not crash um after 1 hours uh in AudioRecorder during stress_test_run"` | `"The service did not crash after 1 hours in AudioRecorder during stress_test_run."` | `140.08 ms` |

---

## 6. Phase D — End-to-End Acoustic Speech (`STTEngine` Whisper CPU $\rightarrow$ `LocalTextRepair` GGUF)

### D1: Real Human Speech (`Mozilla Common Voice 17.0`, `en-cv-001`..`en-cv-010`)
- **Provenance:** 10 consented real human English voice recordings (`16 kHz` mono PCM WAV, `private/corpus/en/en-cv-001.wav`..`en-cv-010.wav`, manifest [`docs/evaluation/EN_HI_TA_ML_REAL_VOICE_MANIFEST.json`](./EN_HI_TA_ML_REAL_VOICE_MANIFEST.json)), including 5 negation-bearing clips (`no`, `cannot`, `not`) and 5 general declarative clips.
- **Pipeline:** `WAV bytes` $\rightarrow$ `STTEngine` (`faster-whisper` `base` int8 CPU) $\rightarrow$ `LocalTextRepair` (`Qwen2.5-0.5B-Instruct-Q4_K_M.gguf`, `MAX_LATENCY_MS=400.0 ms`).
- **Results:**
  - **Completed within $\le 400.0\text{ ms}$:** **`10 / 10 (100.0%)` (`REPAIRED`)**
  - **SLM Repair Latency:** **`P50 = 141.64 ms`**, **`P90 / P95 = 196.52 ms`**, **`Min = 110.55 ms`**, **`Max = 203.71 ms`**
  - **Mean WER vs. Human Reference:** **`0.1428` before repair $\rightarrow$ `0.1428` after repair** (`0.0000` WER degradation)
  - **Post-Delivery Factual Leaks:** **`0 / 10 (0.0%)`**

| Item ID | Whisper Hypothesis (`faster-whisper` `base` int8) | `LocalTextRepair` Output (`Qwen2.5-0.5B`) | STT Decode | SLM Repair | WER Pre $\rightarrow$ Post |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **`en-cv-006`** | `"The examples included are by no means comprehensive."` | `"The examples included are by no means comprehensive."` | `803.58 ms` | **`141.92 ms`** | `0.1111 -> 0.1111` |
| **`en-cv-007`** | `"No one else could claim that."` | `"No one else could claim that."` | `707.82 ms` | **`196.52 ms`** | `0.0000 -> 0.0000` |
| **`en-cv-008`** | `"I cannot understand it."` | `"I cannot understand it."` | `708.64 ms` | **`203.71 ms`** | `0.0000 -> 0.0000` |
| **`en-cv-009`** | `"It's not a ghost, it was probably a hologram."` | `"It's not a ghost, it was probably a hologram."` | `704.60 ms` | **`155.34 ms`** | `0.0000 -> 0.0000` |
| **`en-cv-010`** | `"No intact examples of native vegetation survive in the area immediately around Yay."` | `"No intact examples of native vegetation survive in the area immediately around Yay."` | `669.71 ms` | **`141.36 ms`** | `0.0769 -> 0.0769` |

### D2: Acoustic Disfluency Speech (`Windows SAPI` WAV $\rightarrow$ `STTEngine` Whisper CPU $\rightarrow$ `LocalTextRepair` GGUF)
- **Provenance:** 10 disfluent technical utterances containing spoken `"um"` / `"uh"`, numbers, currency, and negations synthesized to `16 kHz` WAV via Windows `SAPI.SpVoice`, decoded by `STTEngine` (`faster-whisper` `base` int8 CPU), and repaired by `LocalTextRepair`.
- **Results:**
  - **Completed within $\le 400.0\text{ ms}$:** **`10 / 10 (100.0%)` (`REPAIRED`)**
  - **SLM Repair Latency:** **`P50 = 116.25 ms`**, **`P90 / P95 = 148.79 ms`**, **`Min = 83.05 ms`**, **`Max = 153.39 ms`**
  - **Post-Delivery Factual Leaks:** **`0 / 10 (0.0%)`**
  - **Observation on Whisper + Disfluencies:** On acoustic audio, `faster-whisper` automatically suppresses most spoken `"um"`/`"uh"` fillers during ASR decoding (or occasionally transcribes synthetic TTS `"uh"` as `"A"`/`"How"`), and when `"Um"` survives ASR (`"Um there are 60 sweets and we must not skip sweet 14 during validation."`), `LocalTextRepair` strips the leading `"Um"` and re-capitalizes `"There are 60 sweets and we must not skip sweet 14 during validation."` in **`115.42 ms`** with zero factual loss.

> **Remaining Pre-Merge Requirement:** While Phase D1 validates real human Common Voice 17.0 recordings and Phase D2 validates acoustic disfluency waveforms through `faster-whisper`, Common Voice consists of read sentences rather than spontaneous unscripted developer dictation. Interactive live-microphone pilot speech validation on spontaneous human disfluencies remains required before merging `feature/local-slm-repair-sandbox` into `master`.
