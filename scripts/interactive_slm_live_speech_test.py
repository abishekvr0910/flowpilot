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

import numpy as np
import sounddevice as sd
from engine.audio_devices import get_audio_input_devices
from engine.audio_recorder import AudioRecorder
from engine.evaluation_metrics import verify_critical_facts
from engine.local_text_repair import LocalTextRepair
from engine.stt_engine import STTEngine
from scripts.interactive_physical_mic_test import classify_hardware_bus

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


def play_beep(freq: int = 880, duration: float = 0.25):
    """Plays an audible beep through the laptop speakers (and fallback default device)."""
    try:
        sr = 48000
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        beep_mono = (0.4 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
        beep_stereo = np.column_stack([beep_mono, beep_mono])
        for i, d in enumerate(sd.query_devices()):
            if "speaker" in d["name"].lower() and d["max_output_channels"] >= 2 and d["hostapi"] == 2:
                try:
                    sd.play(beep_stereo, samplerate=sr, device=i)
                    sd.wait()
                    return
                except Exception:
                    pass
        sd.play(beep_mono, samplerate=sr)
        sd.wait()
    except Exception:
        try:
            import winsound
            winsound.Beep(freq, int(duration * 1000))
        except Exception:
            pass


def compute_pcm16_rms_and_peak(pcm_bytes: bytes) -> tuple[float, float]:
    if not pcm_bytes or len(pcm_bytes) < 2:
        return 0.0, 0.0
    count = len(pcm_bytes) // 2
    samples = struct.unpack(f"<{count}h", pcm_bytes[: count * 2])
    sum_sq = sum((s / 32768.0) ** 2 for s in samples)
    peak = max(abs(s) / 32768.0 for s in samples)
    return math.sqrt(sum_sq / count), peak


def get_physical_wasapi_mics() -> list[dict]:
    """Returns all physical WASAPI microphone input devices."""
    devices = get_audio_input_devices(refresh=True)
    wasapi_candidates = [
        d for d in devices
        if d.get("host_api") == "Windows WASAPI"
        and "cable" not in d["name"].lower()
        and "virtual" not in d["name"].lower()
        and "stereo mix" not in d["name"].lower()
    ]
    if not wasapi_candidates:
        wasapi_candidates = [
            d for d in devices
            if "cable" not in d["name"].lower() and "virtual" not in d["name"].lower()
        ]
    return wasapi_candidates


def record_multi_mic_clip(
    recorders: list[tuple[dict, AudioRecorder]], duration_sec: float = 6.0
) -> list[tuple[dict, bytes, float, float]]:
    for _, rec in recorders:
        rec.start_recording()
    time.sleep(duration_sec)
    results: list[tuple[dict, bytes, float, float]] = []
    for dev, rec in recorders:
        wav_bytes = rec.stop_recording(keep_stream_alive=True)
        if not wav_bytes or len(wav_bytes) <= 44:
            results.append((dev, b"", 0.0, 0.0))
            continue
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            pcm_bytes = wf.readframes(wf.getnframes())
        rms, peak = compute_pcm16_rms_and_peak(pcm_bytes)
        if peak > 0.002 and peak < 0.35:
            count = len(pcm_bytes) // 2
            samples = struct.unpack(f"<{count}h", pcm_bytes[: count * 2])
            gain = min(8.0, 0.55 / peak)
            scaled = [max(-32767, min(32767, int(s * gain))) for s in samples]
            pcm_bytes = struct.pack(f"<{len(scaled)}h", *scaled)
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf_out:
                wf_out.setnchannels(1)
                wf_out.setsampwidth(2)
                wf_out.setframerate(16000)
                wf_out.writeframes(pcm_bytes)
            wav_bytes = buf.getvalue()
            rms, peak = compute_pcm16_rms_and_peak(pcm_bytes)
        results.append((dev, wav_bytes, rms, peak))
    results.sort(key=lambda item: item[2], reverse=True)
    return results


def resolve_gguf_model(explicit_path: Path | None) -> Path:
    if explicit_path and explicit_path.is_file():
        return explicit_path
    for cand in DEFAULT_GGUF_PATHS:
        if cand.is_file():
            return cand
    raise FileNotFoundError("Could not locate qwen2.5-0.5b-instruct-q4_k_m.gguf; pass --model <path>.")


def ensure_windows_mic_unmuted(keyword: str = "array") -> bool:
    """Uses pycaw to verify and enforce unmuted status and 100% volume for the target microphone."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        for d in AudioUtilities.GetAllDevices():
            name = getattr(d, 'FriendlyName', '') or ''
            if keyword.lower() in name.lower() and hasattr(d, '_dev') and d._dev:
                ep = d._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                vol = cast(ep, POINTER(IAudioEndpointVolume))
                if vol.GetMute():
                    vol.SetMute(0, None)
                    print(f"[Windows Audio] Unmuted {name}", flush=True)
                if vol.GetMasterVolumeLevelScalar() < 0.95:
                    vol.SetMasterVolumeLevelScalar(1.0, None)
                    print(f"[Windows Audio] Set {name} volume to 100%", flush=True)
                return True
    except Exception as exc:
        print(f"[Windows Audio] pycaw inspection note: {exc}", flush=True)
    return False


def run_live_test(
    model_path: Path,
    duration_sec: float,
    out_receipt: Path,
    min_rms: float = 0.002,
    interactive: bool = False,
    target_mic: str = "array",
) -> int:
    print("=" * 74, flush=True)
    print("  FLOWPILOT SPONTANEOUS LIVE MICROPHONE + LOCAL SLM REPAIR GATE", flush=True)
    print("=" * 74, flush=True)

    ensure_windows_mic_unmuted(target_mic)

    all_candidates = get_physical_wasapi_mics()
    array_candidates = [d for d in all_candidates if target_mic.lower() in (d.get("name") or "").lower()]
    candidates = array_candidates if array_candidates else all_candidates

    for d in candidates:
        b_info = classify_hardware_bus(d.get("name") or "", host_api=d.get("host_api") or "Windows WASAPI")
        print(
            f"[Device] Armed Mic  : [{d.get('index')}] {d.get('name')} ({d.get('host_api')}) "
            f"-> {b_info.get('parent_pnp_instance_id')} ({b_info.get('hardware_bus_class')})",
            flush=True,
        )

    target = candidates[0]
    dev_idx = target.get("index")
    dev_name = target.get("name") or "Unknown"
    host_api = target.get("host_api") or "Windows WASAPI"
    bus_info = classify_hardware_bus(dev_name, host_api=host_api)

    print(f"[Model]  Loading STT (faster-whisper base int8) and GGUF ({model_path.name})...", flush=True)
    stt = STTEngine({
        "engine_mode": "local",
        "local_model_size": "base",
        "cpu_threads": min(8, os.cpu_count() or 4),
        "biasing_strategy": "none",
        "vad_filter": False,
    })
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

    recorders = [(d, AudioRecorder(device_index=d.get("index"))) for d in candidates]
    trials = []
    repair_latencies = []
    within_400ms = 0
    fact_leaks = 0

    try:
        for idx, prompt_cfg in enumerate(LIVE_PROMPTS, start=1):
            print("\n" + "-" * 74, flush=True)
            print(f"[Trial {idx}/{len(LIVE_PROMPTS)}] ({prompt_cfg['id']})", flush=True)
            print(f"Prompt: {prompt_cfg['instruction']}", flush=True)
            if interactive:
                try:
                    input("  -> Press [ENTER] when ready to speak this prompt... ")
                except (EOFError, KeyboardInterrupt):
                    pass
            wav_bytes, rms, peak = b"", 0.0, 0.0
            raw_text = ""
            stt_ms = 0.0

            for attempt in range(1, 21):
                print(f"  [Window {attempt}/20] Listening ({duration_sec:.1f}s) after HIGH BEEP — SPEAK NOW!", flush=True)
                play_beep(880, duration=0.3)
                time.sleep(0.4)
                captured_list = record_multi_mic_clip(recorders, duration_sec=duration_sec)
                best_dev, wav_bytes, rms, peak = captured_list[0]
                if rms < min_rms:
                    print(f"    (Silence RMS={rms:.5f} < {min_rms}; waiting for your voice...)", flush=True)
                    continue

                for cand_dev, cand_wav, cand_rms, cand_peak in captured_list:
                    if cand_rms < min_rms:
                        continue
                    t0 = time.perf_counter()
                    stt_res = stt.transcribe(cand_wav, language="en")
                    stt_ms = (time.perf_counter() - t0) * 1000.0
                    candidate = (stt_res.get("text") or "").strip() if isinstance(stt_res, dict) else str(stt_res).strip()
                    print(f"    [{cand_dev.get('index')} {cand_dev.get('name')[:25]}] RMS={cand_rms:.5f} -> STT ({stt_ms:.0f}ms): '{candidate}'", flush=True)
                    if len(candidate.split()) >= 2 and not candidate.lower().startswith("you"):
                        raw_text = candidate
                        wav_bytes, rms, peak = cand_wav, cand_rms, cand_peak
                        dev_idx = cand_dev.get("index")
                        dev_name = cand_dev.get("name") or dev_name
                        host_api = cand_dev.get("host_api") or host_api
                        bus_info = classify_hardware_bus(dev_name, host_api=host_api)
                        play_beep(523, duration=0.18)
                        time.sleep(0.1)
                        play_beep(659, duration=0.18)
                        print(
                            f"  Captured speech on [{dev_idx}] {dev_name}: RMS={rms:.5f}, Peak={peak:.4f}",
                            flush=True,
                        )
                        break
                if raw_text:
                    time.sleep(2.0)
                    break

            if not raw_text:
                print(f"  [FAIL] No spoken utterance captured for {prompt_cfg['id']} after 20 windows.", flush=True)
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

            print(f"  Whisper Raw ({stt_ms:6.1f} ms): {raw_text}", flush=True)
            print(f"  SLM Repaired ({rep.latency_ms:5.1f} ms): {rep.text} [{rep.status.value}] | fact_leak={leak}", flush=True)

            trials.append({
                "trial_id": prompt_cfg["id"],
                "instruction": prompt_cfg["instruction"],
                "device_index": dev_idx,
                "device_name": dev_name,
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
        for _, rec in recorders:
            rec.close()
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
    print("\n" + "=" * 74, flush=True)
    print(f"  LIVE SPEECH RECEIPT WRITTEN: {out_receipt}", flush=True)
    print(f"  SHA-256: {receipt['receipt_sha256']}", flush=True)
    print(f"  VERDICT: {'PASS' if receipt['summary']['gate_passed'] else 'FAIL'}", flush=True)
    print("=" * 74, flush=True)
    return 0 if receipt["summary"]["gate_passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=None, help="Path to GGUF model")
    parser.add_argument("--duration-sec", type=float, default=6.0, help="Recording duration per prompt in seconds")
    parser.add_argument(
        "--out-receipt",
        type=Path,
        default=PROJECT_ROOT / "docs" / "evaluation" / "LOCAL_SLM_LIVE_HUMAN_SPEECH_RECEIPT.json",
    )
    parser.add_argument("--interactive", action="store_true", help="Prompt Enter key in terminal before each trial")
    parser.add_argument("--target-mic", type=str, default="array", help="Microphone name filter keyword (default: array)")
    args = parser.parse_args()
    sys.exit(
        run_live_test(
            resolve_gguf_model(args.model),
            args.duration_sec,
            args.out_receipt,
            interactive=args.interactive,
            target_mic=args.target_mic,
        )
    )
