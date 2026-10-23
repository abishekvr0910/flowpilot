"""Offline WAV evaluation; missing recordings never become simulated ASR scores.

Reports decode/format duration, not stop-to-visible-text latency. RSS is sampled,
not a peak measurement. This runner does not perform network instrumentation.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psutil
from engine.stt_engine import STTEngine
from engine.context_processor import ContextProcessor
from engine.evaluation_metrics import (
    calculate_wer, calculate_cer, verify_critical_facts, calculate_formatted_quality_score,
)
from engine.real_voice_corpus import RealVoiceCorpus, get_dev_smoke_corpus
from benchmarks.runtime_metrics import collect_runtime_environment, summarize_processing_trials


def get_current_rss_mb():
    """One sample of this process tree's resident memory; not peak RSS."""
    try:
        process = psutil.Process(os.getpid())
        return round(sum(p.memory_info().rss for p in [process, *process.children(recursive=True)]) / 1048576, 2)
    except psutil.Error:
        return None


def run_evaluation(manifest_path: Optional[Path] = None, model_size="base",
                   limit: Optional[int] = None, output_report: Optional[Path] = None,
                   include_text=False):
    if limit is not None and limit < 0:
        raise ValueError("limit must be nonnegative")
    corpus = RealVoiceCorpus.load_manifest(manifest_path) if manifest_path is not None else get_dev_smoke_corpus()
    valid, errors = corpus.validate_integrity()
    if not valid:
        raise ValueError("Invalid corpus: " + "; ".join(errors))
    items = corpus.items if limit is None else corpus.items[:limit]
    root = manifest_path.resolve().parent if manifest_path is not None else PROJECT_ROOT
    initial_rss = get_current_rss_mb()
    environment = collect_runtime_environment(PROJECT_ROOT)
    stt = processor = None
    results = []
    for item in items:
        row = {"item_id": item.item_id, "language": item.language, "group": item.group,
               "status": "missing_audio", "wer": None, "cer": None,
               "fact_accuracy": None, "facts_preserved": None,
               "quality_score": None, "decode_sec": None, "format_sec": None}
        results.append(row)
        audio_path = Path(item.audio_file) if item.audio_file else None
        if audio_path is not None and not audio_path.is_absolute():
            audio_path = root / audio_path
        if audio_path is None or not audio_path.is_file():
            continue
        if item.consent_verified is not True:
            row["status"] = "consent_required"
            continue
        try:
            # First decode includes lazy loading; template-only runs load nothing.
            if stt is None:
                stt = STTEngine({"local_model_size": model_size, "cpu_threads": min(8, os.cpu_count() or 4)})
                processor = ContextProcessor({"active_tone_mode": "developer"})
            wav = audio_path.read_bytes()
            phase = "warm" if stt.get_model_status()["status"] == "ready" else "cold"
            row["phase"] = phase
            cpu_start = time.process_time()
            start = time.perf_counter()
            raw = stt.transcribe(wav, language=item.language)
            if raw.get("error"):
                raise RuntimeError("recognizer reported failure")
            hypothesis = raw["text"]
            if not isinstance(hypothesis, str):
                raise TypeError("recognizer output is not text")
            decode_sec = time.perf_counter() - start
            start = time.perf_counter()
            formatted = processor.process(hypothesis,
                active_window={"window_title": "Evaluation", "process_name": "code.exe"},
                session_mode="developer", language=item.language)
            format_sec = time.perf_counter() - start
            process_cpu_sec = time.process_time() - cpu_start
            facts = verify_critical_facts(item.spoken_reference, hypothesis, item.language)
            missing_critical = (facts["missing_numbers"] + facts["missing_negations"]
                                + facts["missing_identifiers"])
            added_critical = [value for values in facts["added_entities"].values() for value in values]
            row.update(status="evaluated",
                wer=calculate_wer(item.spoken_reference, hypothesis, item.language),
                cer=calculate_cer(item.spoken_reference, hypothesis, item.language),
                fact_accuracy=facts["accuracy"], facts_preserved=facts["preserved"],
                missing_critical=missing_critical, added_critical=added_critical,
                quality_score=calculate_formatted_quality_score(item.formatted_reference, formatted, item.language),
                decode_sec=round(decode_sec, 4), format_sec=round(format_sec, 4),
                process_cpu_sec=round(process_cpu_sec, 4),
                processing_cpu_percent=round(100 * process_cpu_sec / max(decode_sec + format_sec, 1e-9), 2),
                sampled_rss_mb=get_current_rss_mb())
            if include_text:
                row.update(spoken_ref=item.spoken_reference, hypothesis=hypothesis,
                           formatted_ref=item.formatted_reference, formatted_hyp=formatted)
        except Exception as exc:
            row.update(status="failed", error_type=type(exc).__name__)

    measured = [r for r in results if r["status"] == "evaluated"]
    aggregate = {
        "status": "complete" if results and len(measured) == len(results) else "incomplete",
        "model_size": model_size, "total_items": len(results),
        "evaluated_items": len(measured),
        "missing_audio_items": sum(r["status"] == "missing_audio" for r in results),
        "failed_items": sum(r["status"] == "failed" for r in results),
        "consent_required_items": sum(r["status"] == "consent_required" for r in results),
        "initial_rss_mb": initial_rss, "final_sampled_rss_mb": get_current_rss_mb(),
        "latency_boundary": "WAV decode + formatting only; first decode includes lazy model load; no OS injection",
        "network_verification": "not instrumented by this runner",
        "languages": {},
        "runtime": {
            "environment": environment,
            "cpu_threads": min(8, os.cpu_count() or 4),
            "timing": summarize_processing_trials(results),
            "cpu_boundary": "Evaluator process CPU seconds during decode and formatting; percent may exceed 100 across cores",
            "memory_boundary": "Process tree RSS sampled after each successful trial; not peak memory or desktop HUD usage",
            "unmeasured": ["visible_delivery", "desktop_cold_start", "recording_cpu", "companion_cpu", "peak_memory", "long_session_growth"],
        },
    }
    if measured:
        try:
            model_file = Path(STTEngine.resolve_model_path(model_size)) / "model.bin"
            if model_file.is_file():
                digest = hashlib.sha256()
                with model_file.open("rb") as model_stream:
                    for block in iter(lambda: model_stream.read(1048576), b""):
                        digest.update(block)
                aggregate["runtime"]["model_sha256"] = digest.hexdigest()
        except OSError as exc:
            aggregate["runtime"]["model_fingerprint_error"] = type(exc).__name__
    for language in sorted({r["language"] for r in results}):
        rows = [r for r in measured if r["language"] == language]
        stats = {"count": len(rows), "requested_items": sum(r["language"] == language for r in results)}
        for output, key in (("avg_wer", "wer"), ("avg_cer", "cer"),
                            ("fact_accuracy", "fact_accuracy"), ("quality_score", "quality_score"),
                            ("avg_decode_sec", "decode_sec")):
            stats[output] = round(sum(r[key] for r in rows) / len(rows), 4) if rows else None
        aggregate["languages"][language] = stats
    print(f"Evaluation {aggregate['status']}: {len(measured)}/{len(results)} recorded items measured; "
          f"{aggregate['missing_audio_items']} missing audio; {aggregate['failed_items']} failures.")
    if output_report is not None:
        output_report.parent.mkdir(parents=True, exist_ok=True)
        output_report.write_text(json.dumps({"timestamp": time.time(), "summary": aggregate,
                                             "trials": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return aggregate


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "docs/evaluation/DEV_SMOKE_CORPUS_MANIFEST.json")
    parser.add_argument("--model", default="base", choices=["base", "small"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "scratch/evaluation/real_voice_report.json")
    parser.add_argument("--include-text", action="store_true", help="Explicitly include consented transcripts in the local report")
    args = parser.parse_args()
    report = run_evaluation(args.manifest, args.model, args.limit, args.output, args.include_text)
    sys.exit(0 if report["status"] == "complete" else 2)
