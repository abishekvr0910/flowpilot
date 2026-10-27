"""
Benchmark Real GGUF Model (Qwen2.5-0.5B-Instruct-Q4_K_M.gguf) in Process-Isolated LocalTextRepair Sandbox.
Measures:
1. Phase 0 (Cold-Start Audit):
   - Unwarmed first-call fallback latency (must return FALLBACK_UNPROVISIONED without blocking dictation).
   - Background worker cold-start initialization latency (ms) and initial worker RSS (MB).
   - First warm call latency (ms).
2. Phase A (150-Case Adversarial Corpus + Gold-Output Exact Match Audit):
   - End-to-end CPU inference latency distribution (P50, P90, P95, Mean, Min, Max) across all 150 utterances.
   - Guard-pass rate (REPAIRED) AND Gold-Output Exact Match rate (res.text == expected_gold).
   - Post-delivery factual integrity (must be 0% entity/negation/identifier loss or hallucination).
3. Phase B (30-Case Edge-Case Gold Suite: Natural @N, Filler-in-Meaning, Acronyms, Interrogatives):
   - Evaluates natural @0/@1/<SLOT_0> inputs, subject/meta/quoted filler-in-meaning, ER/Ah units, and questions.
   - Measures Gold Exact Match rate and latency under the strict 400.0 ms deadline.
4. Phase C (25-Case Strict 400 ms Production Deadline Stress Test):
   - Enforces MAX_LATENCY_MS = 400.0 ms and tracks peak worker RSS across the entire 205-call session.
"""

import argparse
import datetime
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

import psutil

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.evaluation_metrics import calculate_wer, verify_critical_facts
from engine.local_text_repair import LocalTextRepair, RepairStatus, SpanDiffEditor, SlotLocker


def build_150_adversarial_corpus_with_gold() -> list[tuple[str, str]]:
    """Constructs 150 (raw_utterance, expected_gold) pairs with numbers, negations, currencies, and identifiers."""
    templates = [
        (
            "um we must not deploy commit {num} to production before {hour} pm because check_status_code returned {err}",
            "We must not deploy commit {num} to production before {hour} pm because check_status_code returned {err}.",
        ),
        (
            "uh please do not charge more than ${price} for invoice {inv} and never overwrite user_profile_id",
            "Please do not charge more than ${price} for invoice {inv} and never overwrite user_profile_id.",
        ),
        (
            "the latency target is {ms} ms at p50 and cannot exceed {max_ms} ms under any circumstances in FlowOrchestrator",
            "The latency target is {ms} ms at p50 and cannot exceed {max_ms} ms under any circumstances in FlowOrchestrator.",
        ),
        (
            "we did not approve the €{price} transfer on {year}-10-27 and won't enable auto_retry_mode today",
            "We did not approve the €{price} transfer on {year}-10-27 and won't enable auto_retry_mode today.",
        ),
        (
            "neither node_{node_a} nor node_{node_b} should accept port {port} when allow_external_access is false",
            "Neither node_{node_a} nor node_{node_b} should accept port {port} when allow_external_access is false.",
        ),
        (
            "um the discount rate is {pct}% for tier_{tier} customers so don't apply the £{price} surcharge",
            "The discount rate is {pct}% for tier_{tier} customers so don't apply the £{price} surcharge.",
        ),
        (
            "verify_critical_facts must never drop the negation in sentence {num} or alter the {pct}% threshold",
            "verify_critical_facts must never drop the negation in sentence {num} or alter the {pct}% threshold.",
        ),
        (
            "uh I said do not delete table_{node_a} until backup_{inv} finishes with 0 errors in AudioRecorder",
            "I said do not delete table_{node_a} until backup_{inv} finishes with 0 errors in AudioRecorder.",
        ),
        (
            "the battery dropped to {pct}% after {hour} hours so we cannot run background_sync_worker right now",
            "The battery dropped to {pct}% after {hour} hours so we cannot run background_sync_worker right now.",
        ),
        (
            "there are {num} suites in run_all_tests and we must not skip suite {node_b} during release validation",
            "There are {num} suites in run_all_tests and we must not skip suite {node_b} during release validation.",
        ),
    ]
    corpus = []
    for i in range(150):
        raw_tpl, gold_tpl = templates[i % len(templates)]
        params = dict(
            num=100 + i,
            hour=(i % 12) + 1,
            err=400 + (i % 5),
            price=f"{(i + 1) * 12.50:.2f}",
            inv=5000 + i,
            ms=150 + (i % 100),
            max_ms=400,
            year=2026,
            node_a=i + 1,
            node_b=i + 2,
            port=8000 + i,
            pct=round(5.5 + (i % 90) * 0.5, 1),
            tier=(i % 4) + 1,
        )
        corpus.append((raw_tpl.format(**params), gold_tpl.format(**params)))
    return corpus


def build_30_edge_case_gold_suite() -> list[dict]:
    """Constructs 30 hard edge cases covering natural @N, filler-in-meaning, ER/Ah units, and questions."""
    base_cases = [
        {
            "category": "natural_at_n_tail",
            "raw": "um please ping @0 and @1 before {n} pm so check_user_handle does not fail",
            "gold": "Please ping @0 and @1 before {n} pm so check_user_handle does not fail.",
        },
        {
            "category": "natural_at_n_head",
            "raw": "@0 and @1 must not accept port {port} when allow_external_access is false",
            "gold": "@0 and @1 must not accept port {port} when allow_external_access is false.",
        },
        {
            "category": "literal_slot_token",
            "raw": "uh do not replace <SLOT_0> or @99 when testing SlotLocker with {n} inputs",
            "gold": "Do not replace <SLOT_0> or @99 when testing SlotLocker with {n} inputs.",
        },
        {
            "category": "filler_in_meaning_subject",
            "raw": "um is a common filler word that should not break parse_token_stream in {port}",
            "gold": "Um is a common filler word that should not break parse_token_stream in {port}.",
        },
        {
            "category": "filler_in_meaning_meta_mention",
            "raw": "uh please do not delete the word um or the token uh when running suite {n}",
            "gold": "Please do not delete the word um or the token uh when running suite {n}.",
        },
        {
            "category": "filler_in_meaning_quoted",
            "raw": "um we should not strip 'um' or \"uh\" from raw_transcript_buffer during {n} runs",
            "gold": "We should not strip 'um' or \"uh\" from raw_transcript_buffer during {n} runs.",
        },
        {
            "category": "acronym_and_unit_homographs",
            "raw": "uh the patient in ER room {n} must not wait um more than 15 minutes for a 50 Ah battery",
            "gold": "The patient in ER room {n} must not wait more than 15 minutes for a 50 Ah battery.",
        },
        {
            "category": "interrogative_why",
            "raw": "um why did check_status_code return {port} instead of 200 when retry_limit_enabled was not set",
            "gold": "Why did check_status_code return {port} instead of 200 when retry_limit_enabled was not set?",
        },
        {
            "category": "interrogative_can",
            "raw": "uh can we deploy commit {port} before {n} pm without breaking user_session_id",
            "gold": "Can we deploy commit {port} before {n} pm without breaking user_session_id?",
        },
        {
            "category": "inline_tail_fillers",
            "raw": "the service did not crash um after {n} hours uh in AudioRecorder during stress_test_run",
            "gold": "The service did not crash after {n} hours in AudioRecorder during stress_test_run.",
        },
    ]
    cases = []
    for i in range(30):
        item = base_cases[i % len(base_cases)]
        n_val = (i % 9) + 1
        port_val = 2020 + i
        cases.append({
            "category": item["category"],
            "raw": item["raw"].format(n=n_val, port=port_val),
            "gold": item["gold"].format(n=n_val, port=port_val),
        })
    return cases


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def percentiles(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "p50": None, "p90": None, "p95": None, "mean": None, "min": None, "max": None}
    s = sorted(values)
    n = len(s)
    return {
        "count": n,
        "p50": round(statistics.median(s), 2),
        "p90": round(s[int(0.90 * (n - 1))], 2),
        "p95": round(s[int(0.95 * (n - 1))], 2),
        "mean": round(statistics.mean(s), 2),
        "min": round(min(s), 2),
        "max": round(max(s), 2),
    }


def run_benchmark(model_path: Path, unbounded_ceiling_ms: float = 3000.0, strict_deadline_ms: float = 400.0) -> dict:
    if not model_path.is_file():
        raise FileNotFoundError(f"GGUF model not found: {model_path}")

    print(f"[1] Computing SHA-256 of {model_path.name} ({model_path.stat().st_size:,} bytes)...")
    model_sha256 = sha256_file(model_path)
    print(f"    SHA-256: {model_sha256}")

    config = {
        "local_text_repair_enabled": True,
        "local_text_repair_model_path": str(model_path),
        "local_text_repair_worker_mode": "process",
        "local_text_repair_span_diff": True,
    }
    engine = LocalTextRepair(config=config)
    engine.MAX_LATENCY_MS = strict_deadline_ms

    # Phase 0: Cold-Start Audit (unwarmed call before worker is ready, then wait for ready)
    print("[2] Phase 0: Measuring cold-start fallback & worker initialization...")
    t_cold0 = time.perf_counter()
    cold_res = engine.repair(
        "um we must not deploy commit 100 to production before 1 pm because check_status_code returned 400"
    )
    cold_unwarmed_call_ms = (time.perf_counter() - t_cold0) * 1000.0
    print(
        f"    Cold unwarmed call: status={cold_res.status.value} "
        f"caller_latency={cold_unwarmed_call_ms:.2f} ms (fallback={cold_res.fallback_used})"
    )

    # Now wait for the background worker process spawned by the cold call to finish warming up
    ready = engine._ensure_worker_process(timeout_sec=15.0)
    total_cold_ready_ms = (time.perf_counter() - t_cold0) * 1000.0
    if not ready or engine._worker_process is None:
        engine.shutdown()
        raise RuntimeError("SLM worker process failed to initialize with real GGUF model.")

    worker_pid = engine._worker_process.pid
    worker_proc = psutil.Process(worker_pid)
    worker_initial_rss_mb = worker_proc.memory_info().rss / (1024 * 1024)
    worker_peak_rss_mb = worker_initial_rss_mb

    first_warm_res = engine.repair(
        "um we must not deploy commit 100 to production before 1 pm because check_status_code returned 400"
    )
    print(
        f"    Worker PID {worker_pid} ready in {total_cold_ready_ms:.1f} ms "
        f"(Initial RSS: {worker_initial_rss_mb:.2f} MB) | First warm call: {first_warm_res.latency_ms:.2f} ms"
    )

    corpus = build_150_adversarial_corpus_with_gold()
    engine.MAX_LATENCY_MS = unbounded_ceiling_ms
    latencies_all = []
    latencies_repaired = []
    phase_a_records = []
    status_counts = {s.value: 0 for s in RepairStatus}
    within_400ms_count = 0
    gold_exact_matches = 0
    gold_mismatches = []
    fact_leaks = 0
    repaired_samples = []

    print(
        f"[3] Phase A: Running 150-case adversarial FactGuard, Gold-Output & CPU latency evaluation "
        f"(ceiling={unbounded_ceiling_ms} ms)..."
    )
    try:
        for idx, (raw_text, expected_gold) in enumerate(corpus):
            if not engine._is_ready:
                engine._ensure_worker_process(timeout_sec=15.0)

            res = engine.repair(raw_text, language="en")
            latencies_all.append(res.latency_ms)
            locked_tmp, _ = SlotLocker.lock(raw_text)
            head_tmp, _, _ = SpanDiffEditor.extract_span(locked_tmp)
            phase_a_records.append({
                "index": idx,
                "latency_ms": round(res.latency_ms, 2),
                "head_span": head_tmp,
                "max_tokens": SpanDiffEditor.estimate_max_tokens(head_tmp),
                "status": res.status.value,
                "gold_exact_match": res.text == expected_gold,
            })
            if res.latency_ms <= strict_deadline_ms:
                within_400ms_count += 1
            status_counts[res.status.value] = status_counts.get(res.status.value, 0) + 1
            if res.status == RepairStatus.REPAIRED:
                latencies_repaired.append(res.latency_ms)

            if res.text == expected_gold:
                gold_exact_matches += 1
            elif len(gold_mismatches) < 10:
                gold_mismatches.append({
                    "index": idx,
                    "raw": raw_text,
                    "expected_gold": expected_gold,
                    "actual": res.text,
                    "status": res.status.value,
                })

            facts = verify_critical_facts(raw_text, res.text, language="en")
            missing = facts["missing_numbers"] + facts["missing_negations"] + facts["missing_identifiers"]
            added = [v for vals in facts["added_entities"].values() for v in vals]
            if missing or added:
                fact_leaks += 1

            if (idx + 1) % 25 == 0 or idx < 5:
                curr_rss = worker_proc.memory_info().rss / (1024 * 1024)
                worker_peak_rss_mb = max(worker_peak_rss_mb, curr_rss)
                print(
                    f"    [Phase A {idx + 1:3d}/150] status={res.status.value:<10} "
                    f"latency={res.latency_ms:6.1f} ms | gold_match={res.text == expected_gold} | RSS={curr_rss:.1f} MB"
                )
            if len(repaired_samples) < 6 and res.status == RepairStatus.REPAIRED:
                repaired_samples.append({
                    "raw": raw_text,
                    "expected_gold": expected_gold,
                    "repaired": res.text,
                    "gold_exact_match": res.text == expected_gold,
                    "latency_ms": round(res.latency_ms, 2),
                    "slots_locked": res.slots_locked,
                })

        top_slowest_cases = sorted(phase_a_records, key=lambda r: r["latency_ms"], reverse=True)[:5]

        # Phase B: 30-Case Hard Semantic & Edge-Case Gold Suite under strict 400 ms deadline
        print(
            f"[4] Phase B: Running 30-case Edge-Case Gold Suite "
            f"(Natural @N, Filler-in-Meaning, ER/Ah, Questions; deadline={strict_deadline_ms} ms)..."
        )
        engine.MAX_LATENCY_MS = strict_deadline_ms
        edge_cases = build_30_edge_case_gold_suite()
        edge_latencies = []
        edge_status_counts = {s.value: 0 for s in RepairStatus}
        edge_gold_matches = 0
        edge_gold_mismatches = []
        edge_fact_leaks = 0
        edge_samples = []

        for idx, item in enumerate(edge_cases):
            raw_text = item["raw"]
            expected_gold = item["gold"]
            res = engine.repair(raw_text, language="en")
            edge_latencies.append(res.latency_ms)
            edge_status_counts[res.status.value] = edge_status_counts.get(res.status.value, 0) + 1

            if res.text == expected_gold:
                edge_gold_matches += 1
            else:
                edge_gold_mismatches.append({
                    "index": idx,
                    "category": item["category"],
                    "raw": raw_text,
                    "expected_gold": expected_gold,
                    "actual": res.text,
                    "status": res.status.value,
                })

            facts = verify_critical_facts(raw_text, res.text, language="en")
            missing = facts["missing_numbers"] + facts["missing_negations"] + facts["missing_identifiers"]
            added = [v for vals in facts["added_entities"].values() for v in vals]
            if missing or added:
                edge_fact_leaks += 1

            if idx < 10:
                edge_samples.append({
                    "category": item["category"],
                    "raw": raw_text,
                    "expected_gold": expected_gold,
                    "repaired": res.text,
                    "gold_exact_match": res.text == expected_gold,
                    "latency_ms": round(res.latency_ms, 2),
                })
                print(
                    f"    [Phase B {idx + 1:2d}/30] [{item['category']:<28}] "
                    f"latency={res.latency_ms:6.1f} ms | gold_match={res.text == expected_gold}"
                )

        # Phase C: 25-Case Strict 400 ms Production Deadline Stress Test
        print(
            f"[5] Phase C: Running 25-case strict production deadline stress test "
            f"(MAX_LATENCY_MS={strict_deadline_ms} ms)..."
        )
        strict_latencies = []
        strict_status_counts = {s.value: 0 for s in RepairStatus}
        strict_fact_leaks = 0
        strict_gold_matches = 0
        for idx, (raw_text, expected_gold) in enumerate(corpus[:25]):
            res = engine.repair(raw_text, language="en")
            strict_latencies.append(res.latency_ms)
            strict_status_counts[res.status.value] = strict_status_counts.get(res.status.value, 0) + 1
            if res.text == expected_gold:
                strict_gold_matches += 1

            facts = verify_critical_facts(raw_text, res.text, language="en")
            missing = facts["missing_numbers"] + facts["missing_negations"] + facts["missing_identifiers"]
            added = [v for vals in facts["added_entities"].values() for v in vals]
            if missing or added:
                strict_fact_leaks += 1

        # Phase D: Real Acoustic Speech (Common Voice 17.0 Human WAV + SAPI Disfluent WAV -> STTEngine -> LocalTextRepair)
        print(
            f"[6] Phase D: Running end-to-end Acoustic Speech -> STTEngine (Whisper CPU) -> LocalTextRepair (GGUF)..."
        )
        from engine.stt_engine import STTEngine
        stt = STTEngine({"engine_mode": "local", "local_model_size": "base", "cpu_threads": min(8, os.cpu_count() or 4)})
        stt.preload_model()

        manifest_path = PROJECT_ROOT / "docs" / "evaluation" / "EN_HI_TA_ML_REAL_VOICE_MANIFEST.json"
        manifest_items = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else []
        en_cv_items = [m for m in manifest_items if m.get("language") == "en"]

        cv_results = []
        cv_repair_latencies = []
        cv_within_400ms = 0
        cv_fact_leaks = 0
        cv_wer_before = []
        cv_wer_after = []

        fallback_corpus_root = Path(r"S:\APPs\New folder\private\corpus\en")
        for m in en_cv_items:
            rel_wav = (manifest_path.parent / m["audio_file"]).resolve()
            if not rel_wav.is_file():
                rel_wav = fallback_corpus_root / Path(m["audio_file"]).name
            if not rel_wav.is_file():
                continue
            wav_bytes = rel_wav.read_bytes()
            t_stt0 = time.perf_counter()
            stt_out = stt.transcribe(wav_bytes, language="en")
            stt_ms = (time.perf_counter() - t_stt0) * 1000.0
            stt_text = stt_out.get("text", "").strip() if isinstance(stt_out, dict) else str(stt_out).strip()

            rep_res = engine.repair(stt_text, language="en")
            cv_repair_latencies.append(rep_res.latency_ms)
            if rep_res.latency_ms <= strict_deadline_ms:
                cv_within_400ms += 1

            facts = verify_critical_facts(stt_text, rep_res.text, language="en")
            missing = facts["missing_numbers"] + facts["missing_negations"] + facts["missing_identifiers"]
            added = [v for vals in facts["added_entities"].values() for v in vals]
            if missing or added:
                cv_fact_leaks += 1

            wer_pre = calculate_wer(m["spoken_reference"], stt_text, "en")
            wer_post = calculate_wer(m["spoken_reference"], rep_res.text, "en")
            cv_wer_before.append(wer_pre)
            cv_wer_after.append(wer_post)

            cv_results.append({
                "item_id": m["item_id"],
                "spoken_reference": m["spoken_reference"],
                "whisper_hypothesis": stt_text,
                "slm_repaired": rep_res.text,
                "status": rep_res.status.value,
                "stt_decode_ms": round(stt_ms, 2),
                "slm_repair_ms": round(rep_res.latency_ms, 2),
                "wer_before_repair": round(wer_pre, 4),
                "wer_after_repair": round(wer_post, 4),
                "fact_leak": bool(missing or added),
            })
            print(
                f"    [Phase D1 Human CV {m['item_id']}] stt={stt_ms:5.1f} ms | "
                f"slm={rep_res.latency_ms:5.1f} ms ({rep_res.status.value}) | "
                f"WER {wer_pre:.3f} -> {wer_post:.3f}"
            )

        # Sub-phase D2: 10 Acoustic Disfluent Spoken Utterances via Windows SAPI WAV -> STTEngine -> LocalTextRepair
        sapi_utterances = [
            "um we must not deploy commit 104 to production before 3 pm",
            "uh please do not charge more than 25 dollars for invoice 5010",
            "um the latency target is 170 milliseconds and cannot exceed 400 milliseconds",
            "uh we did not approve the 500 dollar transfer on 2026 10 27",
            "um neither node 1 nor node 2 should accept port 8080 today",
            "uh the discount rate is 15 percent so do not apply the surcharge",
            "um I said do not delete table 5 until backup 90 finishes with 0 errors",
            "uh the battery dropped to 12 percent after 4 hours so we cannot run the worker",
            "um there are 60 suites and we must not skip suite 14 during validation",
            "uh why did the status check return 404 instead of 200 today",
        ]
        sapi_results = []
        sapi_repair_latencies = []
        sapi_within_400ms = 0
        sapi_fact_leaks = 0
        if sys.platform == "win32":
            import tempfile
            import win32com.client

            sp = win32com.client.Dispatch("SAPI.SpVoice")
            fs = win32com.client.Dispatch("SAPI.SpFileStream")
            for idx, spoken_prompt in enumerate(sapi_utterances):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                    tmp_wav = tf.name
                try:
                    fs.Open(tmp_wav, 3)
                    sp.AudioOutputStream = fs
                    sp.Speak(spoken_prompt)
                    fs.Close()
                    wav_bytes = Path(tmp_wav).read_bytes()
                finally:
                    Path(tmp_wav).unlink(missing_ok=True)

                t_stt0 = time.perf_counter()
                stt_out = stt.transcribe(wav_bytes, language="en")
                stt_ms = (time.perf_counter() - t_stt0) * 1000.0
                stt_text = stt_out.get("text", "").strip() if isinstance(stt_out, dict) else str(stt_out).strip()

                rep_res = engine.repair(stt_text, language="en")
                sapi_repair_latencies.append(rep_res.latency_ms)
                if rep_res.latency_ms <= strict_deadline_ms:
                    sapi_within_400ms += 1

                facts = verify_critical_facts(stt_text, rep_res.text, language="en")
                missing = facts["missing_numbers"] + facts["missing_negations"] + facts["missing_identifiers"]
                added = [v for vals in facts["added_entities"].values() for v in vals]
                if missing or added:
                    sapi_fact_leaks += 1

                sapi_results.append({
                    "index": idx,
                    "spoken_prompt": spoken_prompt,
                    "whisper_hypothesis": stt_text,
                    "slm_repaired": rep_res.text,
                    "status": rep_res.status.value,
                    "stt_decode_ms": round(stt_ms, 2),
                    "slm_repair_ms": round(rep_res.latency_ms, 2),
                    "fact_leak": bool(missing or added),
                })
                print(
                    f"    [Phase D2 Acoustic SAPI {idx + 1:2d}/10] stt={stt_ms:5.1f} ms | "
                    f"slm={rep_res.latency_ms:5.1f} ms ({rep_res.status.value})"
                )

        if engine._worker_process and engine._worker_process.is_alive():
            curr_rss = psutil.Process(engine._worker_process.pid).memory_info().rss / (1024 * 1024)
            worker_peak_rss_mb = max(worker_peak_rss_mb, curr_rss)

    finally:
        engine.shutdown(wait=True)

    import llama_cpp

    summary = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "host": {
            "node": platform.node(),
            "system": platform.system(),
            "release": platform.release(),
            "processor": platform.processor(),
            "cpu_count_logical": os.cpu_count(),
            "python": sys.version.split()[0],
            "llama_cpp_version": getattr(llama_cpp, "__version__", "unknown"),
        },
        "model": {
            "name": model_path.name,
            "size_bytes": model_path.stat().st_size,
            "sha256": model_sha256,
            "quantization": "Q4_K_M",
            "parameters": "0.5B",
            "repair_strategy": (
                "span_diff (adaptive 2/3-word opening span + dynamic max_tokens + "
                "@N compact slots + gen-0 gc.collect(0) + ABOVE_NORMAL_PRIORITY_CLASS)"
            ),
            "n_ctx": 256,
            "n_batch": 128,
            "n_threads": min(4, os.cpu_count() or 2),
        },
        "phase_0_cold_start_audit": {
            "cold_unwarmed_call_status": cold_res.status.value,
            "cold_unwarmed_call_fallback_used": cold_res.fallback_used,
            "cold_unwarmed_call_latency_ms": round(cold_unwarmed_call_ms, 2),
            "worker_cold_ready_latency_ms": round(total_cold_ready_ms, 2),
            "first_warm_call_status": first_warm_res.status.value,
            "first_warm_call_latency_ms": round(first_warm_res.latency_ms, 2),
            "worker_initial_rss_mb": round(worker_initial_rss_mb, 2),
            "worker_peak_rss_mb": round(worker_peak_rss_mb, 2),
        },
        "phase_a_150_adversarial_corpus": {
            "corpus_size": len(corpus),
            "ceiling_ms": unbounded_ceiling_ms,
            "strict_sla_target_ms": strict_deadline_ms,
            "completed_within_400ms_count": within_400ms_count,
            "completed_within_400ms_pct": round((within_400ms_count / len(corpus)) * 100.0, 2),
            "status_counts": status_counts,
            "repaired_rate_pct": round((status_counts["REPAIRED"] / len(corpus)) * 100.0, 2),
            "gold_exact_match_count": gold_exact_matches,
            "gold_exact_match_pct": round((gold_exact_matches / len(corpus)) * 100.0, 2),
            "gold_mismatches": gold_mismatches,
            "factguard_veto_rate_pct": round((status_counts["VETOED_FACT_MISMATCH"] / len(corpus)) * 100.0, 2),
            "latency_all_ms": percentiles(latencies_all),
            "latency_repaired_only_ms": percentiles(latencies_repaired),
            "top_slowest_cases": top_slowest_cases,
            "post_delivery_fact_leaks": fact_leaks,
            "repaired_samples": repaired_samples,
        },
        "phase_b_30_edge_case_gold_suite": {
            "sample_size": len(edge_cases),
            "deadline_ms": strict_deadline_ms,
            "status_counts": edge_status_counts,
            "gold_exact_match_count": edge_gold_matches,
            "gold_exact_match_pct": round((edge_gold_matches / len(edge_cases)) * 100.0, 2),
            "gold_mismatches": edge_gold_mismatches,
            "latency_ms": percentiles(edge_latencies),
            "post_delivery_fact_leaks": edge_fact_leaks,
            "samples": edge_samples,
        },
        "phase_c_strict_400ms_deadline_25_cases": {
            "sample_size": 25,
            "deadline_ms": strict_deadline_ms,
            "status_counts": strict_status_counts,
            "gold_exact_match_count": strict_gold_matches,
            "gold_exact_match_pct": round((strict_gold_matches / 25) * 100.0, 2),
            "caller_latency_ms": percentiles(strict_latencies),
            "post_delivery_fact_leaks": strict_fact_leaks,
        },
        "phase_d_real_speech_stt_to_slm_evaluation": {
            "d1_common_voice_17_human_speech": {
                "source": "Mozilla Common Voice 17.0 (en-cv-001..010, consented real human recordings)",
                "sample_size": len(cv_results),
                "completed_within_400ms_count": cv_within_400ms,
                "completed_within_400ms_pct": round((cv_within_400ms / max(1, len(cv_results))) * 100.0, 2),
                "slm_repair_latency_ms": percentiles(cv_repair_latencies),
                "mean_wer_before_repair": round(statistics.mean(cv_wer_before), 4) if cv_wer_before else None,
                "mean_wer_after_repair": round(statistics.mean(cv_wer_after), 4) if cv_wer_after else None,
                "post_delivery_fact_leaks": cv_fact_leaks,
                "samples": cv_results,
            },
            "d2_acoustic_sapi_disfluent_speech": {
                "source": "Windows SAPI WAV synthesis -> STTEngine (faster-whisper base int8 CPU) -> LocalTextRepair",
                "sample_size": len(sapi_results),
                "completed_within_400ms_count": sapi_within_400ms,
                "completed_within_400ms_pct": round((sapi_within_400ms / max(1, len(sapi_results))) * 100.0, 2),
                "slm_repair_latency_ms": percentiles(sapi_repair_latencies),
                "post_delivery_fact_leaks": sapi_fact_leaks,
                "samples": sapi_results,
            },
        },
    }
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Qwen2.5-0.5B GGUF in LocalTextRepair sandbox")
    parser.add_argument("--model", type=Path, required=True, help="Path to GGUF model file")
    parser.add_argument("--ceiling-ms", type=float, default=3000.0, help="Unbounded Phase A ceiling in ms")
    parser.add_argument("--deadline-ms", type=float, default=400.0, help="Strict Phase B/C latency deadline in ms")
    parser.add_argument("--out-json", type=Path, default=None, help="Optional JSON output path")
    args = parser.parse_args()

    result = run_benchmark(
        args.model,
        unbounded_ceiling_ms=args.ceiling_ms,
        strict_deadline_ms=args.deadline_ms,
    )
    print("\n=== BENCHMARK SUMMARY ===")
    print(json.dumps(result, indent=2))
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
