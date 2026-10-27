"""
Interactive Spontaneous Live Human Microphone Dictation Gate for LocalTextRepair Sandbox (Spec 0004).

Captures live spontaneous human speech from the active physical microphone across 5 prompts
(including disfluencies 'um'/'uh', numbers, negations, and technical tokens), decodes each
recording offline via STTEngine (faster-whisper int8 CPU), repairs the transcript via
LocalTextRepair (Qwen2.5-0.5B-Instruct-Q4_K_M.gguf, strict 400.0 ms deadline), verifies
zero factual loss via verify_critical_facts, and writes a SHA-256 signed receipt.
"""

import argparse
import datetime
import hashlib
import io
import json
import math
import os
import platform
import statistics
import struct
import sys
import time
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sounddevice as sd
from engine.audio_recorder import AudioRecorder
from engine.evaluation_metrics import verify_critical_facts
from engine.local_text_repair import LocalTextRepair, RepairStatus
from engine.stt_engine import STTEngine
from scripts.verify_audio_device_gate import classify_hardware_bus

DEFAULT_GGUF_PATHS = [
    Path(r"C:\Users\moham\.gemini\antigravity-cli\brain\8d265aff-d454-486a-b3e9-3f924dbca464\scratch\models\qwen2.5-0.5b-instruct-q4_k_m.gguf"),
    PROJECT_ROOT / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf",
]

LIVE_PROMPTS = [
    {
        "id": "live-01-negation-number",
        "instruction": "Speak naturally with a leading 'um' or 'uh': e.g. 'um we must not deploy build 104 before 3 pm'",
    },
    {
        "id": "live-02-currency-negation",
        "instruction": "Speak naturally with a hesitation: e.g. 'uh please do not charge more than 25 dollars for invoice 500'",
    },
    {
        "id": "live-03-question",
        "instruction": "Ask a spontaneous question with 'um' or 'uh': e.g. 'um why did the status check return 404 instead of 200'",
    },
    {
        "id": "live-04-filler-in-meaning",
        "instruction": "Mention a filler word or unit in meaning: e.g. 'uh the patient in ER room 4 cannot wait 15 minutes'",
    },
    {
        "id": "live-05-free-spontaneous",
        "instruction": "Speak any spontaneous developer sentence with numbers, negations, and natural hesitation",
    },
]


def compute_pcm16_rms_and_peak(pcm_bytes: bytes) -> tuple[float, float]:
    if not pcm_bytes or len(pcm_bytes) < 2:
        return 0.0, 0.0
    count = len(pcm_bytes) // 2
    samples = struct.unpack(f"<{count}h", pcm_bytes[: count * 2])
    sum_sq = sum((s / 32768.0) ** 2 for s in samples)
    peak = max(abs(s) / 32768.0 for s in samples)
    return math.sqrt(sum_sq / count), peak


def record_wav_clip(device_index: int, duration_sec: float = 5.5, sample_rate: int = 16000) -> tuple[bytes, float, float]:
    frames = int(duration_sec * sample_rate)
    audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="int16", device=device_index)
    sd.wait()
    pcm_bytes = audio.tobytes()
    rms, peak = compute_pcm16_rms_and_peak(pcm_bytes)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue(), rms, peak


def resolve_gguf_model(explicit_path: Path | None) -> Path:
    if explicit_path and explicit_path.is_file():
        return explicit_path
    for cand in DEFAULT_GGUF_PATHS:
        if cand.is_file():
            return cand
    raise FileNotFoundError("Could not locate qwen2.5-0.5b-instruct-q4_k_m.gguf; pass --model <path>.")


def run_live_test(model_path: Path, duration_sec: float, out_receipt: Path, min_rms: float = 0.004) -> int:
    print("=" * 74)
    print("  FLOWPILOT SPONTANEOUS LIVE MICROPHONE + LOCAL SLM REPAIR GATE")
    print("=" * 74)

    rec = AudioRecorder()
    resolved = rec.resolve_target_device()
    dev_idx = resolved.get("device_index")
    dev_name = resolved.get("device_name") or "Unknown"
    host_api = resolved.get("host_api") or "WASAPI"
    bus_info = classify_hardware_bus(dev_name, host_api=host_api)
    print(f"[Device] Active Mic : [{dev_idx}] {dev_name} ({host_api})")
    print(f"[Bus]    Hardware ID: {bus_info.get('matched_instance_id')} ({bus_info.get('bus_classification')})")

    print(f"[Model]  Loading STT (faster-whisper base int8) and GGUF ({model_path.name})...")
    stt = STTEngine({"engine_mode": "local", "local_model_size": "base", "cpu_threads": min(8, os.cpu_count() or 4)})
    stt.preload_model()

    repairer = LocalTextRepair(
        config={
            "local_text_repair_enabled": True,
            "local_text_repair_model_path": str(model_path),
            "local_text_repair_worker_mode": "process",
            "local_text_repair_span_diff": True,
        }
    )
    repairer.MAX_LATENCY_MS = 400.0
    if not repairer._ensure_worker_process(timeout_sec=15.0):
        repairer.shutdown()
        raise RuntimeError("Failed to warm up LocalTextRepair GGUF worker process.")

    trials = []
    repair_latencies = []
    within_400ms = 0
    fact_leaks = 0

    try:
        for idx, prompt_cfg in enumerate(LIVE_PROMPTS, start=1):
            print("\n" + "-" * 74)
            print(f"[Trial {idx}/{len(LIVE_PROMPTS)}] ({prompt_cfg['id']})")
            print(f"Prompt: {prompt_cfg['instruction']}")
            print(f"Recording {duration_sec:.1f}s in 1 second... SPEAK NOW!")
            time.sleep(1.0)

            wav_bytes, rms, peak = record_wav_clip(dev_idx, duration_sec=duration_sec)
            print(f"  Captured audio: RMS={rms:.5f}, Peak={peak:.4f}")
            if rms < min_rms:
                print(f"  [FAIL] RMS {rms:.5f} is below silence floor {min_rms}; real human voice required.")
                return 2

            t0 = time.perf_counter()
            stt_res = stt.transcribe(wav_bytes, language="en")
            stt_ms = (time.perf_counter() - t0) * 1000.0
            raw_text = (stt_res.get("text") or "").strip() if isinstance(stt_res, dict) else str(stt_res).strip()
            if not raw_text:
                print("  [FAIL] Whisper decoded empty text from microphone recording.")
                return 2

            rep = repairer.repair(raw_text, language="en")
            repair_latencies.append(rep.latency_ms)
            if rep.latency_ms <= 400.0:
                within_400ms += 1

            facts = verify_critical_facts(raw_text, rep.text, language="en")
            missing = facts["missing_numbers"] + facts["missing_negations"] + facts["missing_identifiers"]
            added = [v for vals in facts["added_entities"].values() for v in vals]
            leak = bool(missing or added)
            if leak:
                fact_leaks += 1

            print(f"  Whisper Raw ({stt_ms:6.1f} ms): {raw_text}")
            print(f"  SLM Repaired ({rep.latency_ms:5.1f} ms): {rep.text} [{rep.status.value}] | fact_leak={leak}")

            trials.append({
                "trial_id": prompt_cfg["id"],
                "instruction": prompt_cfg["instruction"],
                "rms_energy": round(rms, 5),
                "peak_amplitude": round(peak, 4),
                "stt_decode_ms": round(stt_ms, 2),
                "whisper_raw": raw_text,
                "slm_repaired": rep.text,
                "slm_status": rep.status.value,
                "slm_latency_ms": round(rep.latency_ms, 2),
                "within_400ms": rep.latency_ms <= 400.0,
                "fact_leak": leak,
                "missing_facts": missing,
                "added_facts": added,
            })
    finally:
        repairer.shutdown(wait=True)

    receipt = {
        "schema": "flowpilot.slm.live_human_speech_receipt.v1",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "host": {
            "node": platform.node(),
            "system": platform.system(),
            "release": platform.release(),
            "python": sys.version.split()[0],
        },
        "microphone": {
            "device_index": dev_idx,
            "device_name": dev_name,
            "host_api": host_api,
            "hardware_bus": bus_info,
        },
        "model": {
            "name": model_path.name,
            "size_bytes": model_path.stat().st_size,
        },
        "summary": {
            "trials_count": len(trials),
            "completed_within_400ms_count": within_400ms,
            "completed_within_400ms_pct": round((within_400ms / len(trials)) * 100.0, 2),
            "p50_latency_ms": round(statistics.median(repair_latencies), 2),
            "max_latency_ms": round(max(repair_latencies), 2),
            "post_delivery_fact_leaks": fact_leaks,
            "gate_passed": within_400ms == len(trials) and fact_leaks == 0,
        },
        "trials": trials,
    }
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt["receipt_sha256"] = hashlib.sha256(canonical).hexdigest().upper()

    out_receipt.parent.mkdir(parents=True, exist_ok=True)
    out_receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("\n" + "=" * 74)
    print(f"  LIVE SPEECH RECEIPT WRITTEN: {out_receipt}")
    print(f"  SHA-256: {receipt['receipt_sha256']}")
    print(f"  VERDICT: {'PASS' if receipt['summary']['gate_passed'] else 'FAIL'}")
    print("=" * 74)
    return 0 if receipt["summary"]["gate_passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=None, help="Path to GGUF model")
    parser.add_argument("--duration-sec", type=float, default=5.5, help="Recording duration per prompt in seconds")
    parser.add_argument(
        "--out-receipt",
        type=Path,
        default=PROJECT_ROOT / "docs" / "evaluation" / "LOCAL_SLM_LIVE_HUMAN_SPEECH_RECEIPT.json",
    )
    args = parser.parse_args()
    sys.exit(run_live_test(resolve_gguf_model(args.model), args.duration_sec, args.out_receipt))
