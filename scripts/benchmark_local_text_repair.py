"""
Benchmark Real GGUF Model (Qwen2.5-0.5B-Instruct-Q4_K_M.gguf) in Process-Isolated LocalTextRepair Sandbox.
Measures:
1. Worker process cold-start warmup latency (ms) and child process RSS memory delta (MB).
2. Phase A (150-Case Full Corpus CPU Latency & Three-Tier FactGuard Audit):
   - End-to-end CPU inference latency distribution (P50, P90, P95, Mean, Min, Max) across all 150 adversarial utterances.
   - Percentage of utterances completing within the strict 400 ms SLA budget on CPU.
   - Three-Tier Guard Protocol efficacy: REPAIRED vs VETOED_FACT_MISMATCH counts, and post-delivery factual integrity
     (must be 0% entity/negation/identifier loss or hallucination across all 150 cases).
3. Phase B (25-Case Strict 400 ms Deadline Enforcement & Process-Isolation Stress Test):
   - Enforces MAX_LATENCY_MS = 400.0 ms with OS-level worker termination and raw-transcript fallback.
   - Verifies bounded caller latency and 0% post-delivery factual leaks under hard timeouts.
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

from engine.evaluation_metrics import verify_critical_facts
from engine.local_text_repair import LocalTextRepair, RepairStatus


def build_150_adversarial_corpus() -> list[str]:
    """Constructs a deterministic 150-utterance adversarial corpus with numbers, negations, currencies, and identifiers."""
    templates = [
        "um we must not deploy commit {num} to production before {hour} pm because check_status_code returned {err}",
        "uh please do not charge more than ${price} for invoice {inv} and never overwrite user_profile_id",
        "the latency target is {ms} ms at p50 and cannot exceed {max_ms} ms under any circumstances in FlowOrchestrator",
        "we did not approve the €{price} transfer on {year}-10-27 and won't enable auto_retry_mode today",
        "neither node_{node_a} nor node_{node_b} should accept port {port} when allow_external_access is false",
        "um the discount rate is {pct}% for tier_{tier} customers so don't apply the £{price} surcharge",
        "verify_critical_facts must never drop the negation in sentence {num} or alter the {pct}% threshold",
        "uh I said do not delete table_{node_a} until backup_{inv} finishes with 0 errors in AudioRecorder",
        "the battery dropped to {pct}% after {hour} hours so we cannot run background_sync_worker right now",
        "there are {num} suites in run_all_tests and we must not skip suite {node_b} during release validation",
    ]
    corpus = []
    for i in range(150):
        tpl = templates[i % len(templates)]
        utterance = tpl.format(
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
        corpus.append(utterance)
    return corpus


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
    engine.MAX_LATENCY_MS = unbounded_ceiling_ms

    print("[2] Warming up isolated SLM worker process (loading GGUF + KV prefix warmup)...")
    t_w0 = time.perf_counter()
    ready = engine._ensure_worker_process(timeout_sec=15.0)
    warmup_ms = (time.perf_counter() - t_w0) * 1000.0
    if not ready or engine._worker_process is None:
        engine.shutdown()
        raise RuntimeError("SLM worker process failed to initialize with real GGUF model.")

    worker_pid = engine._worker_process.pid
    worker_rss_mb = psutil.Process(worker_pid).memory_info().rss / (1024 * 1024)
    print(f"    Worker PID {worker_pid} ready in {warmup_ms:.1f} ms (Worker RSS: {worker_rss_mb:.1f} MB)")

    corpus = build_150_adversarial_corpus()
    latencies_all = []
    latencies_repaired = []
    latencies_vetoed = []
    status_counts = {s.value: 0 for s in RepairStatus}
    within_400ms_count = 0
    fact_leaks = 0
    repaired_samples = []
    vetoed_samples = []

    print(
        f"[3] Phase A: Running 150-case adversarial FactGuard & CPU latency evaluation "
        f"(ceiling={unbounded_ceiling_ms} ms)..."
    )
    try:
        for idx, raw_text in enumerate(corpus):
            if not engine._is_ready:
                engine._ensure_worker_process(timeout_sec=15.0)

            res = engine.repair(raw_text, language="en")
            latencies_all.append(res.latency_ms)
            if res.latency_ms <= strict_deadline_ms:
                within_400ms_count += 1
            status_counts[res.status.value] = status_counts.get(res.status.value, 0) + 1
            if res.status == RepairStatus.REPAIRED:
                latencies_repaired.append(res.latency_ms)
            elif res.status == RepairStatus.VETOED_FACT_MISMATCH:
                latencies_vetoed.append(res.latency_ms)

            # Verify post-delivery text strictly preserves all numbers, negations, and identifiers
            facts = verify_critical_facts(raw_text, res.text, language="en")
            missing = facts["missing_numbers"] + facts["missing_negations"] + facts["missing_identifiers"]
            added = [v for vals in facts["added_entities"].values() for v in vals]
            if missing or added:
                fact_leaks += 1

            if idx < 5 or (idx + 1) % 25 == 0:
                print(
                    f"    [Phase A {idx + 1:3d}/150] status={res.status.value:<22} "
                    f"latency={res.latency_ms:6.1f} ms | slots={res.slots_locked}"
                )
            if len(repaired_samples) < 6 and res.status == RepairStatus.REPAIRED:
                repaired_samples.append({
                    "raw": raw_text,
                    "repaired": res.text,
                    "latency_ms": round(res.latency_ms, 2),
                    "slots_locked": res.slots_locked,
                })
            if len(vetoed_samples) < 4 and res.status == RepairStatus.VETOED_FACT_MISMATCH:
                vetoed_samples.append({
                    "raw": raw_text,
                    "delivered_fallback": res.text,
                    "veto_reason": res.veto_reason,
                    "latency_ms": round(res.latency_ms, 2),
                    "slots_locked": res.slots_locked,
                })

        if engine._worker_process and engine._worker_process.is_alive():
            try:
                worker_rss_mb = max(
                    worker_rss_mb,
                    psutil.Process(engine._worker_process.pid).memory_info().rss / (1024 * 1024),
                )
            except Exception:
                pass

        # Phase B: Strict 400 ms Production Deadline Enforcement & Process-Kill Stress Test (25 utterances)
        print(
            f"[4] Phase B: Running 25-case strict production deadline stress test "
            f"(MAX_LATENCY_MS={strict_deadline_ms} ms)..."
        )
        engine.MAX_LATENCY_MS = strict_deadline_ms
        strict_latencies = []
        strict_status_counts = {s.value: 0 for s in RepairStatus}
        strict_fact_leaks = 0
        for idx, raw_text in enumerate(corpus[:25]):
            res = engine.repair(raw_text, language="en")
            strict_latencies.append(res.latency_ms)
            strict_status_counts[res.status.value] = strict_status_counts.get(res.status.value, 0) + 1

            facts = verify_critical_facts(raw_text, res.text, language="en")
            missing = facts["missing_numbers"] + facts["missing_negations"] + facts["missing_identifiers"]
            added = [v for vals in facts["added_entities"].values() for v in vals]
            if missing or added:
                strict_fact_leaks += 1

            if idx < 5 or (idx + 1) % 5 == 0:
                print(
                    f"    [Phase B {idx + 1:2d}/25] status={res.status.value:<22} "
                    f"caller_latency={res.latency_ms:6.2f} ms | fallback={res.fallback_used}"
                )

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
            "repair_strategy": "span_diff (3-word opening span + @N compact slot encoding)",
            "n_ctx": 128,
            "n_batch": 64,
            "n_threads": min(4, os.cpu_count() or 2),
        },
        "warmup": {
            "warmup_latency_ms": round(warmup_ms, 2),
            "worker_peak_rss_mb": round(worker_rss_mb, 2),
        },
        "phase_a_unbounded_150_corpus": {
            "corpus_size": len(corpus),
            "ceiling_ms": unbounded_ceiling_ms,
            "strict_sla_target_ms": strict_deadline_ms,
            "completed_within_400ms_count": within_400ms_count,
            "completed_within_400ms_pct": round((within_400ms_count / len(corpus)) * 100.0, 2),
            "status_counts": status_counts,
            "repaired_rate_pct": round((status_counts["REPAIRED"] / len(corpus)) * 100.0, 2),
            "factguard_veto_rate_pct": round((status_counts["VETOED_FACT_MISMATCH"] / len(corpus)) * 100.0, 2),
            "latency_all_ms": percentiles(latencies_all),
            "latency_repaired_only_ms": percentiles(latencies_repaired),
            "latency_vetoed_only_ms": percentiles(latencies_vetoed),
            "post_delivery_fact_leaks": fact_leaks,
            "repaired_samples": repaired_samples,
            "vetoed_samples": vetoed_samples,
        },
        "phase_b_strict_400ms_deadline_25_cases": {
            "sample_size": 25,
            "deadline_ms": strict_deadline_ms,
            "status_counts": strict_status_counts,
            "caller_latency_ms": percentiles(strict_latencies),
            "post_delivery_fact_leaks": strict_fact_leaks,
        },
    }
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Qwen2.5-0.5B GGUF in LocalTextRepair sandbox")
    parser.add_argument("--model", type=Path, required=True, help="Path to GGUF model file")
    parser.add_argument("--ceiling-ms", type=float, default=3000.0, help="Unbounded Phase A ceiling in ms")
    parser.add_argument("--deadline-ms", type=float, default=400.0, help="Strict Phase B latency deadline in ms")
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
