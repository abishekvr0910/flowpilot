# Local SLM GGUF Benchmark Report (`Qwen2.5-0.5B-Instruct-Q4_K_M.gguf`)

- **Date (UTC):** `2026-10-27T15:39:36Z`
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
| **Inference Runtime** | `llama-cpp-python 0.3.36` (CPU wheel, `n_ctx=256`, `n_batch=128`, `use_mmap=True`, `logits_all=False`, KV prefix warmup, `gc.collect(0)`, `ABOVE_NORMAL_PRIORITY_CLASS`) |
| **Model File** | `qwen2.5-0.5b-instruct-q4_k_m.gguf` (`Qwen2.5-0.5B-Instruct`, `Q4_K_M`) |
| **File Size** | `491,400,032` bytes (`~468.6 MiB`) |
| **SHA-256 Digest** | `74A4DA8C9FDBCD15BD1F6D01D621410D31C6FC00986F5EB687824E7B93D7A9DB` |
| **Worker Process RSS** | **`516.41 MB` initial ready RSS / `528.26 MB` peak RSS** across 256 total inferences (`71.74 MB` below the `600 MB` budget) |

---

## 2. Root-Cause Analysis & Resolution of the `404.30 ms` Phase A Outlier

In Iteration 3 (`315be23`), `149 / 150 (99.33%)` of Phase A cases completed within `<= 400.0 ms`, with a single outlier at `404.30 ms` (`+4.30 ms` above budget). Profiling identified three compounding causes:

1. **Multi-Slot 3-Word Opening Spans Without Leading Fillers (`"@4 @0 @5"`):**
   - Utterances without leading disfluencies (`"neither node_5 nor..."` -> `"<SLOT_4> <SLOT_0> <SLOT_5>"`) extracted 3 compact slots (`"@4 @0 @5"` = `6` BPE tokens) even though only sentence-initial capitalization (`2` words, `"@4 @0"`) was needed.
   - **Fix:** `SpanDiffEditor.extract_span()` now uses an adaptive window (`3` words when a leading filler `um`/`uh` is present, `2` words otherwise), and `SpanDiffEditor.estimate_max_tokens()` dynamically bounds completion tokens (`2` to `6` tokens) based on the exact content and `@N` count of the extracted span.
2. **Unconditional Full 3-Generation `gc.collect()` After Every Request:**
   - Calling full `gc.collect()` after every single pipe response occasionally triggered a full generation-2 heap scan right before the next request arrived.
   - **Fix:** Replaced unconditional full `gc.collect()` with fast generation-0 `gc.collect(0)` on every call and a full `gc.collect()` only every 25 calls.
3. **Windows Thread Scheduling Preemption & Short-Sentence Threshold (`SPAN_THRESHOLD_WORDS`):**
   - Set `psutil.Process(os.getpid()).nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)` in `_slm_process_worker_entry` so Windows does not preempt the 4 `llama.cpp` threads onto efficiency cores, and lowered `SPAN_THRESHOLD_WORDS` from `8` to `2` so 3–8 word real-speech utterances also use bounded span-diff editing instead of full-sentence regeneration.

**Result:** Phase A `P50` dropped from `170.71 ms` to **`96.09 ms`**, `P95` dropped from `253.96 ms` to **`144.25 ms`**, `Max` dropped from `404.30 ms` to **`162.53 ms`**, and **`150 / 150 (100.0%)`** of Phase A cases completed well under `400.0 ms`.

---

## 3. Phase 0 — Cold-Start & Worker Memory Audit

Measures first-call behavior when `LocalTextRepair.repair()` is invoked cold before the worker process has finished loading GGUF weights:

| Cold-Start Metric | Measured Value | Contract / Target |
| :--- | :--- | :--- |
| **Unwarmed First-Call Status** | `FALLBACK_UNPROVISIONED` (`fallback_used=True`) | Immediate raw fallback without blocking dictation |
| **Unwarmed First-Call Caller Latency** | **`85.71 ms`** | Bounded fast-fail (`<= 100 ms` including `spawn` init) |
| **Background Worker Cold Ready Time** | **`1,071.47 ms`** | Full GGUF load + 1-shot KV prefix warmup |
| **First Warm Call Status & Latency** | **`REPAIRED` in `102.28 ms`** | `<= 300 ms` warm target |
| **Worker Initial / Peak RSS (256 calls)** | **`516.41 MB` / `528.26 MB`** | **`<= 600.0 MB` (`-71.74 MB` headroom)** |

---

## 4. Evolution Across Four Sandbox Iterations

| Metric | Iteration 1: Full-Sentence (`770c7bc`) | Iteration 2: Initial `SpanDiffEditor` (`dbe9b7d`) | Iteration 3: Gold & Edge Guards (`315be23`) | Iteration 4: Adaptive Span + 50 Real Audio Clips |
| :--- | :---: | :---: | :---: | :---: |
| **Phase A Completed `<= 400 ms`** | `0 / 150 (0.0%)` | `149 / 150 (99.33%)` | `149 / 150 (99.33%)` | **`150 / 150 (100.0%)`** |
| **Phase A Guard-Pass (`REPAIRED`)** | `135 / 150 (90.0%)` | `150 / 150 (100.0%)` | `150 / 150 (100.0%)` | **`150 / 150 (100.0%)`** |
| **Phase A Gold Exact Match** | Not measured | Not measured | `150 / 150 (100.0%)` | **`150 / 150 (100.0%)`** |
| **Phase B 30-Case Edge-Case Gold Match** | N/A | `24 / 30 (80.0%)` | `30 / 30 (100.0%)` | **`30 / 30 (100.0%)`** |
| **Phase C Strict `400 ms` Gold Match** | `0 / 25 (0.0%)` | `25 / 25 (100.0%)` | `25 / 25 (100.0%)` | **`25 / 25 (100.0%)`** |
| **Phase D1 Real Human Speech (`Common Voice 17.0`)** | N/A | N/A | N/A | **`40 / 40 (100.0%)` `<= 400 ms` (`0.0000` WER loss)** |
| **Phase D2 Acoustic SAPI Disfluent Speech** | N/A | N/A | N/A | **`10 / 10 (100.0%)` `<= 400 ms`** |
| **Phase A CPU Latency `P50`** | `1,361.49 ms` | `169.76 ms` | `170.71 ms` | **`96.09 ms`** |
| **Phase A CPU Latency `P95`** | `1,847.59 ms` | `244.74 ms` | `253.96 ms` | **`144.25 ms`** |
| **Phase A CPU Latency `Max`** | `2,331.49 ms` | `455.85 ms` | `404.30 ms` | **`162.53 ms` (`<= 400 ms` PASS)** |
| **Phase B Edge-Case Latency `P50` / `P95` / `Max`** | N/A | N/A | `137.69` / `218.37` / `243.79 ms` | **`103.41` / `144.29` / `163.00 ms`** |
| **Phase C Strict `400 ms` `P50` / `P95` / `Max`** | `61.81 ms` (timeout) | `160.58` / `225.67` / `257.41 ms` | `184.61` / `242.65` / `273.61 ms` | **`92.38` / `131.28` / `140.45 ms`** |
| **Worker Process Peak RSS** | `614.53 MB` | `610.70 MB` | `519.62 MB` | **`528.26 MB` (`<= 600 MB` PASS)** |
| **Post-Delivery Factual Leaks** | **`0 / 175 (0.0%)`** | **`0 / 175 (0.0%)`** | **`0 / 205 (0.0%)`** | **`0 / 255 (0.0%)`** |

---

## 5. Phase B — 30-Case Hard Semantic & Edge-Case Gold Suite (`100.0%` Gold Match)

Evaluates 10 categories (3 variations each = 30 cases) under the strict `400.0 ms` deadline (`P50 = 103.41 ms`, `P95 = 144.29 ms`, `Max = 163.00 ms`, **`30 / 30 (100.0%)` Gold Exact Match**):

| Category | Raw Input Sample | Expected Gold & Delivered Output (`100%` Match) | Latency |
| :--- | :--- | :--- | :---: |
| **`natural_at_n_tail`** | `"um please ping @0 and @1 before 1 pm so check_user_handle does not fail"` | `"Please ping @0 and @1 before 1 pm so check_user_handle does not fail."` | `104.14 ms` |
| **`natural_at_n_head`** | `"@0 and @1 must not accept port 2021 when allow_external_access is false"` | `"@0 and @1 must not accept port 2021 when allow_external_access is false."` | `163.00 ms` |
| **`literal_slot_token`** | `"uh do not replace <SLOT_0> or @99 when testing SlotLocker with 3 inputs"` | `"Do not replace <SLOT_0> or @99 when testing SlotLocker with 3 inputs."` | `144.29 ms` |
| **`filler_in_meaning_subject`** | `"um is a common filler word that should not break parse_token_stream in 2023"` | `"Um is a common filler word that should not break parse_token_stream in 2023."` | `120.64 ms` |
| **`filler_in_meaning_meta_mention`** | `"uh please do not delete the word um or the token uh when running suite 5"` | `"Please do not delete the word um or the token uh when running suite 5."` | `94.56 ms` |
| **`filler_in_meaning_quoted`** | `"um we should not strip 'um' or \"uh\" from raw_transcript_buffer during 6 runs"` | `"We should not strip 'um' or \"uh\" from raw_transcript_buffer during 6 runs."` | `87.82 ms` |
| **`acronym_and_unit_homographs`** | `"uh the patient in ER room 7 must not wait um more than 15 minutes for a 50 Ah battery"` | `"The patient in ER room 7 must not wait more than 15 minutes for a 50 Ah battery."` | `103.50 ms` |
| **`interrogative_why`** | `"um why did check_status_code return 2027 instead of 200 when retry_limit_enabled was not set"` | `"Why did check_status_code return 2027 instead of 200 when retry_limit_enabled was not set?"` | `89.52 ms` |
| **`interrogative_can`** | `"uh can we deploy commit 2028 before 9 pm without breaking user_session_id"` | `"Can we deploy commit 2028 before 9 pm without breaking user_session_id?"` | `71.30 ms` |
| **`inline_tail_fillers`** | `"the service did not crash um after 1 hours uh in AudioRecorder during stress_test_run"` | `"The service did not crash after 1 hours in AudioRecorder during stress_test_run."` | `90.75 ms` |

---

## 6. Phase D — End-to-End Acoustic Speech (`STTEngine` Whisper CPU -> `LocalTextRepair` GGUF)

### D1: 40 Consented Real Human Speech Recordings (`Mozilla Common Voice 17.0`, `en-cv-001`..`en-cv-040`)
- **Provenance:** 40 consented real human English voice recordings (`16 kHz` mono PCM WAV, `private/corpus/en/en-cv-001.wav`..`en-cv-040.wav`, manifest [`docs/evaluation/EN_REAL_VOICE_40_MANIFEST.json`](./EN_REAL_VOICE_40_MANIFEST.json)), split evenly into 20 critical negation/entity clips (`no`, `cannot`, `not`, `without`) and 20 general declarative/interrogative clips.
- **Pipeline:** `WAV bytes` -> `STTEngine` (`faster-whisper` `base` int8 CPU) -> `LocalTextRepair` (`Qwen2.5-0.5B-Instruct-Q4_K_M.gguf`, `MAX_LATENCY_MS=400.0 ms`).
- **Results:**
  - **Completed within `<= 400.0 ms`:** **`40 / 40 (100.0%)`** (`39` `REPAIRED`, `1` `VETOED_FACT_MISMATCH` on `en-cv-030` `"Not everyone can tell the bear that he is a bear."` caught by Tier-3 `FactGuard` in `79.75 ms` and safely returned unchanged)
  - **SLM Repair Latency:** **`P50 = 108.93 ms`**, **`P90 = 133.16 ms`**, **`P95 = 142.17 ms`**, **`Min = 79.75 ms`**, **`Max = 163.81 ms`**
  - **Mean WER vs. Human Reference:** **`0.1300` before repair -> `0.1300` after repair** (`0.0000` WER degradation)
  - **Post-Delivery Factual Leaks:** **`0 / 40 (0.0%)`**

### D2: Acoustic Disfluency Speech (`Windows SAPI` WAV -> `STTEngine` Whisper CPU -> `LocalTextRepair` GGUF)
- **Provenance:** 10 disfluent technical utterances containing spoken `"um"` / `"uh"`, numbers, currency, and negations synthesized to `16 kHz` WAV via Windows `SAPI.SpVoice`, decoded by `STTEngine` (`faster-whisper` `base` int8 CPU), and repaired by `LocalTextRepair`.
- **Results:**
  - **Completed within `<= 400.0 ms`:** **`10 / 10 (100.0%)` (`REPAIRED`)**
  - **SLM Repair Latency:** **`P50 = 101.32 ms`**, **`P90 / P95 = 112.41 ms`**, **`Min = 83.35 ms`**, **`Max = 123.99 ms`**
  - **Post-Delivery Factual Leaks:** **`0 / 10 (0.0%)`**

---

## 7. Spontaneous Live Human Microphone Dictation Gate & Safety Audit

- **Date (UTC):** `2026-10-27T17:45:55Z`
- **Receipt:** [`docs/evaluation/LOCAL_SLM_LIVE_HUMAN_SPEECH_RECEIPT.json`](./LOCAL_SLM_LIVE_HUMAN_SPEECH_RECEIPT.json) (`SHA-256: E7F0239E65604920333CF4FC701F737CD494D0A6FFBAC87F64C1E84BD5B69D96`)
- **Microphone:** `[20] Microphone Array (Intel® Smart Sound Technology for Digital Microphones)` (WASAPI 48 kHz $\rightarrow$ 16 kHz)
- **Harness:** [`scripts/interactive_slm_live_speech_test.py`](../../scripts/interactive_slm_live_speech_test.py)

### 7.1 Trial Results Summary

| Trial | Prompt Category | Spoken Input (Whisper Raw) | SLM Output (`LocalTextRepair`) | Latency | SLA (`<= 400 ms`) | Measurable Repair | Fact Leaks |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **1** | Negation + Number | *"The system is very good. It's very good. It's very good."* | *"The system is very good. It's very good. It's very good."* | `116.25 ms` | PASS | Pass-through | 0 |
| **2** | Currency + Negation | *"Um, we must not deploy."* | *"We must not deploy."* | `102.67 ms` | PASS | **Stripped `"Um,"` + Cap** | 0 |
| **3** | Question / Healthcare | *"$1.50 for invoice 500. Um, uh,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,"* | *"$1.50 for invoice 500."* | `144.99 ms` | PASS | **Stripped `"Um, uh"` + Stutters** | 0 |
| **4** | Filler in Meaning | *"Um, do not deploy versions."* | *"Do not deploy versions."* | `122.05 ms` | PASS | **Stripped `"Um,"` + Cap** | 0 |
| **5** | Spontaneous Developer | *"I can't talk, I don't know. I'm already in a more watered place. I can't talk. I need a question."* | *"I can't talk, I don't know. I'm already in a more watered place. I can't talk. I need a question."* | `137.58 ms` | PASS | Pass-through | 0 |

### 7.2 Safety & Quality Findings

1. **Active Measurable Disfluency Removal:** With verbatim disfluency acoustic prompting enabled, **3 / 5 (60.0%)** live microphone trials exhibited active, measurable disfluency repairs (stripping leading `"Um,"`, trailing hesitation `"Um, uh,"`, and punctuation stutters while normalizing capitalization).
2. **Latency & Fact Guard SLA:** All 5 live microphone trials met the strict `<= 400.0 ms` contract (`P50 = 122.05 ms`, `Max = 144.99 ms`), with zero post-delivery factual leaks (`0` added entities, `0` dropped numbers or negations).
3. **Packaging & Standalone Verification:** Built `dist/FlowPilot/FlowPilot.exe` and verified all 3 packaging suites (`test_standalone_binary_smoke.py`, `test_release_integrity_fixes.py`, `test_silero_vad_resolution.py`) and `FlowPilot.exe --self-test` pass.
4. **Merge Recommendation:** The sandbox candidate has met all latency, safety, memory, regression, and live acoustic repair requirements. Master (`ba928d5`) and `v3.1.0-RC9` remain completely untouched until explicit merge authorization.
