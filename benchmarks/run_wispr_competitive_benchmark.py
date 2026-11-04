"""
FlowPilot vs. Cloud-Class (Wispr Flow) Competitive Benchmark Suite.

Evaluates 5 real-world competitive dimensions using authentic human speech clips
and deterministic pipeline instrumentation (zero synthetic ASR scores, zero cloud egress):

  Track 1: Early Speech-Onset Capture (650 ms pre-hotkey speech lead-in via AudioRecorder)
  Track 2: 48 kHz Native WASAPI Downsampling Anti-Aliasing Fidelity
  Track 3: Multilingual Real-Voice Accuracy (Tamil CV-10, User Casual Tanglish 05..16, Polish CV-10)
  Track 4: Active-Window Context Vocabulary & Multilingual Self-Correction Accuracy
  Track 5: Multi-Clause (7-9s) Stop-Action-to-Formatted-Text Latency (P50 / P95 ms)
"""

import argparse
import io
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import soundfile as sf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.audio_recorder import AudioRecorder, resample_audio
from engine.context_processor import ContextProcessor
from engine.evaluation_metrics import calculate_cer, calculate_wer, verify_critical_facts
from engine.onnx_asr.harness import get_specialist_harness
from engine.stt_engine import STTEngine
from engine.transliteration import apply_transliteration_if_enabled
from engine.window_inspector import WindowInspector


EN_MANIFEST = PROJECT_ROOT / "docs" / "evaluation" / "EN_HI_TA_ML_REAL_VOICE_MANIFEST.json"
TA_PL_MANIFEST = PROJECT_ROOT / "docs" / "evaluation" / "TAMIL_POLISH_REAL_VOICE_MANIFEST.json"
TA_CONV_MANIFEST = PROJECT_ROOT / "docs" / "evaluation" / "TAMIL_POLISH_BENCHMARK_CORPUS.json"


def _resolve_audio(manifest_path: Path, rel_or_id: str, lang: str) -> Optional[Path]:
    cand = (manifest_path.parent / rel_or_id).resolve() if ("/" in rel_or_id or "\\" in rel_or_id) else None
    if cand and cand.is_file():
        return cand
    p2 = PROJECT_ROOT / "private" / "corpus" / lang / f"{rel_or_id}.wav"
    if p2.is_file():
        return p2
    return None


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, max(0, int(round((pct / 100.0) * (len(s) - 1)))))
    return round(float(s[idx]), 2)


def run_track1_onset_capture(stt_en: STTEngine, en_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Feeds 500ms room tone + 650ms of actual speech BEFORE start_recording() fires."""
    rng = np.random.default_rng(42)
    wers: List[float] = []
    chunk = 320  # 20ms @ 16kHz

    for item in en_items[:10]:
        wav_path = _resolve_audio(EN_MANIFEST, item.get("audio_file", item["item_id"]), "en")
        if not wav_path:
            continue
        audio, sr = sf.read(str(wav_path), dtype="float32")
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1).astype(np.float32)
        if sr != 16000:
            audio = resample_audio(audio, int(sr), 16000)

        # Strip leading digital silence so speech truly starts at sample 0 of `speech`
        abs_a = np.abs(audio)
        active_idx = np.where(abs_a > 0.025)[0]
        speech = audio[max(0, int(active_idx[0]) - 320):] if len(active_idx) > 0 else audio
        if len(speech) < 16000:
            continue

        rec = AudioRecorder(sample_rate=16000, channels=1)
        # Simulate hot stream so start_recording() harvests _preroll_buffer directly
        class _DummyHotStream:
            active = True
            def abort(self): pass
            def close(self): pass

        rec.stream = _DummyHotStream()
        rec._last_callback_at = time.monotonic()

        # 500ms quiet room noise + 650ms early spoken words BEFORE hotkey press
        quiet = (rng.normal(0.0, 0.0015, size=8000)).astype(np.float32)
        early_samples = int(0.65 * 16000)
        pre_hotkey_stream = np.concatenate([quiet, speech[:early_samples]])
        for pos in range(0, len(pre_hotkey_stream), chunk):
            frame = pre_hotkey_stream[pos:pos + chunk].reshape(-1, 1)
            rec._audio_callback(frame, len(frame), None, None)

        rec.start_recording()

        # Remaining speech AFTER hotkey press
        rem = speech[early_samples:]
        for pos in range(0, len(rem), chunk):
            frame = rem[pos:pos + chunk].reshape(-1, 1)
            rec._audio_callback(frame, len(frame), None, None)

        wav_out = rec.stop_recording(keep_stream_alive=False)
        arr_out = rec.get_last_audio_array()
        res = stt_en.transcribe(arr_out if arr_out is not None else wav_out, language="en")
        wers.append(calculate_wer(item["spoken_reference"], res.get("text", ""), "en"))

    return {
        "clips_evaluated": len(wers),
        "early_onset_650ms_wer_pct": round(100.0 * statistics.mean(wers), 2) if wers else None,
    }


def run_track2_48khz_antialiasing(stt_en: STTEngine, en_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Tests 48 kHz -> 16 kHz resampling under realistic ultrasonic/HF preamp noise (10-20 kHz)."""
    rng = np.random.default_rng(101)
    clean_wers: List[float] = []
    hf_wers: List[float] = []

    for item in en_items[:10]:
        wav_path = _resolve_audio(EN_MANIFEST, item.get("audio_file", item["item_id"]), "en")
        if not wav_path:
            continue
        audio16, sr = sf.read(str(wav_path), dtype="float32")
        if audio16.ndim > 1:
            audio16 = np.mean(audio16, axis=1).astype(np.float32)
        if sr != 16000:
            audio16 = resample_audio(audio16, int(sr), 16000)

        res_clean = stt_en.transcribe(audio16, language="en")
        clean_wers.append(calculate_wer(item["spoken_reference"], res_clean.get("text", ""), "en"))

        # Smoothly upsample clean 16 kHz speech to 48 kHz, then add out-of-band 11-19 kHz preamp interference
        n48 = len(audio16) * 3
        t48 = np.arange(n48, dtype=np.float32) / 48000.0
        up48 = np.interp(
            np.linspace(0.0, len(audio16), n48, endpoint=False),
            np.arange(len(audio16), dtype=np.float32),
            audio16,
        ).astype(np.float32)
        # Out-of-band HF interference strictly above 8 kHz Nyquist of 16 kHz!
        hf_interference = (
            0.12 * np.sin(2.0 * np.pi * 11500.0 * t48)
            + 0.12 * np.sin(2.0 * np.pi * 14200.0 * t48)
            + 0.10 * np.sin(2.0 * np.pi * 17300.0 * t48)
            + 0.05 * rng.normal(0.0, 1.0, size=n48) * np.sin(2.0 * np.pi * 15000.0 * t48)
        ).astype(np.float32)
        noisy48 = up48 + hf_interference

        down16 = resample_audio(noisy48, 48000, 16000)
        res_hf = stt_en.transcribe(down16, language="en")
        hf_wers.append(calculate_wer(item["spoken_reference"], res_hf.get("text", ""), "en"))

    return {
        "clips_evaluated": len(hf_wers),
        "clean_16khz_wer_pct": round(100.0 * statistics.mean(clean_wers), 2) if clean_wers else None,
        "48khz_hf_resampled_wer_pct": round(100.0 * statistics.mean(hf_wers), 2) if hf_wers else None,
        "aliasing_wer_penalty_pct": round(100.0 * (statistics.mean(hf_wers) - statistics.mean(clean_wers)), 2) if hf_wers else None,
    }


def run_track3_multilingual(stt_pl_small: STTEngine) -> Dict[str, Any]:
    """Evaluates Tamil CV-10, User Casual Tanglish (ta-conv-05..16), and Polish CV-10."""
    ic = get_specialist_harness()
    manifest = json.loads(TA_PL_MANIFEST.read_text(encoding="utf-8"))
    ta_cv = [x for x in manifest if x["language"] == "ta"]
    pl_cv = [x for x in manifest if x["language"] == "pl"]

    ta_cv_wers, ta_cv_cers, ta_cv_ms = [], [], []
    for item in ta_cv:
        p = _resolve_audio(TA_PL_MANIFEST, item["item_id"], "ta")
        if not p:
            continue
        wav = p.read_bytes()
        t0 = time.perf_counter()
        res = ic.transcribe(wav, language="ta")
        ta_cv_ms.append((time.perf_counter() - t0) * 1000.0)
        ta_cv_wers.append(calculate_wer(item["spoken_reference"], res["text"], "ta"))
        ta_cv_cers.append(calculate_cer(item["spoken_reference"], res["text"], "ta"))

    # User's own casual voice clips ta-conv-05..16
    conv_items = json.loads(TA_CONV_MANIFEST.read_text(encoding="utf-8"))
    user_clips = [
        x for x in conv_items
        if x["item_id"].startswith("ta-conv-") and 5 <= int(x["item_id"].split("-")[-1]) <= 16
    ]
    conv_ta_wers, conv_tanglish_wers = [], []
    for item in user_clips:
        p = _resolve_audio(TA_CONV_MANIFEST, item.get("audio_file", item["item_id"]), "ta")
        if not p:
            continue
        res = ic.transcribe(p.read_bytes(), language="ta")
        raw_ta = res["text"]
        tanglish = apply_transliteration_if_enabled(raw_ta, "ta", {"tamil_script_mode": "tanglish"})
        conv_ta_wers.append(calculate_wer(item["spoken_reference"], raw_ta, "ta"))
        if item.get("tanglish_reference"):
            conv_tanglish_wers.append(calculate_wer(item["tanglish_reference"], tanglish, "en"))

    pl_wers, pl_cers = [], []
    for item in pl_cv:
        p = _resolve_audio(TA_PL_MANIFEST, item["item_id"], "pl")
        if not p:
            continue
        res = stt_pl_small.transcribe(p.read_bytes(), language="pl")
        pl_wers.append(calculate_wer(item["spoken_reference"], res["text"], "pl"))
        pl_cers.append(calculate_cer(item["spoken_reference"], res["text"], "pl"))

    return {
        "tamil_cv_wer_pct": round(100.0 * statistics.mean(ta_cv_wers), 2) if ta_cv_wers else None,
        "tamil_cv_cer_pct": round(100.0 * statistics.mean(ta_cv_cers), 2) if ta_cv_cers else None,
        "tamil_cv_avg_ms": round(statistics.mean(ta_cv_ms), 1) if ta_cv_ms else None,
        "user_casual_tamil_wer_pct": round(100.0 * statistics.mean(conv_ta_wers), 2) if conv_ta_wers else None,
        "user_casual_tanglish_wer_pct": round(100.0 * statistics.mean(conv_tanglish_wers), 2) if conv_tanglish_wers else None,
        "polish_cv_wer_pct": round(100.0 * statistics.mean(pl_wers), 2) if pl_wers else None,
        "polish_cv_cer_pct": round(100.0 * statistics.mean(pl_cers), 2) if pl_cers else None,
    }


def run_track4_context_and_self_correction() -> Dict[str, Any]:
    """Evaluates active-window symbol harvesting + multilingual self-correction & FactGuard."""
    proc = ContextProcessor({"active_tone_mode": "developer"})

    cases = [
        # (raw_transcript, lang, window_info, surrounding_text, expected_substring, critical_check_ref)
        (
            "deploy on port 8080 scratch that port 8765",
            "en",
            {"title": "server.py - flowpilot - Visual Studio Code", "process_name": "code.exe", "category": "developer"},
            "DEFAULT_PORT = 8765\nclass OnnxASRHarness:",
            "8765",
            "deploy on port 8765",
        ),
        (
            "schedule the call for Tuesday wait no Wednesday at 4 pm",
            "en",
            {"title": "Slack - Engineering", "process_name": "slack.exe", "category": "chat"},
            "",
            "Wednesday",
            "schedule the call for Wednesday at 4 pm",
        ),
        (
            "update onnx asr harness and call selection rewriter",
            "en",
            {"title": "harness.py - flowpilot - Visual Studio Code", "process_name": "code.exe", "category": "developer"},
            "from engine.onnx_asr.harness import OnnxASRHarness\nfrom engine.selection_rewriter import SelectionRewriter\n",
            "OnnxASRHarness",
            "update OnnxASRHarness and call SelectionRewriter",
        ),
        (
            "spotkajmy się we wtorek nie czekaj w środę",
            "pl",
            {"title": "Notatnik", "process_name": "notepad.exe", "category": "document"},
            "",
            "środę",
            "spotkajmy się w środę",
        ),
        (
            "wyślij 5 kopii przepraszam 10 kopii",
            "pl",
            {"title": "Outlook", "process_name": "outlook.exe", "category": "email"},
            "",
            "10 kopii",
            "wyślij 10 kopii",
        ),
        (
            "we must never expose the access token",
            "en",
            {"title": "security.py - Visual Studio Code", "process_name": "code.exe", "category": "developer"},
            "def verify_access_token(access_token: str):",
            "never",
            "we must never expose the access token",
        ),
    ]

    exact_hits = 0
    wers = []
    harvested_count = 0
    extractor = getattr(WindowInspector, "extract_context_vocabulary", None)

    for raw, lang, win, surr, must_contain, target_ref in cases:
        ctx_vocab = extractor(win, surr) if callable(extractor) else []
        harvested_count += len(ctx_vocab)
        # Pass context_vocabulary if ContextProcessor supports it, else standard call
        try:
            out = proc.process(raw, win, session_mode="developer", language=lang, preceding_text=surr, context_vocabulary=ctx_vocab)
        except TypeError:
            out = proc.process(raw, win, session_mode="developer", language=lang, preceding_text=surr)

        # Verify superseded token was removed AND target preserved
        superseded_removed = True
        if "8080" in raw and "8080" in out:
            superseded_removed = False
        if "Tuesday" in raw and "Tuesday" in out:
            superseded_removed = False
        if "wtorek" in raw and "wtorek" in out.lower():
            superseded_removed = False
        if "5 kopii" in raw and "5 " in out:
            superseded_removed = False

        if must_contain in out and superseded_removed:
            exact_hits += 1
        wers.append(calculate_wer(target_ref, out, lang))

    return {
        "cases": len(cases),
        "exact_intent_and_symbol_pass_rate_pct": round(100.0 * exact_hits / len(cases), 2),
        "formatted_wer_pct": round(100.0 * statistics.mean(wers), 2),
        "context_symbols_harvested": harvested_count,
    }


def run_track5_post_stop_latency(stt_en: STTEngine, en_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Measures Stop-Action-to-Formatted-Text latency (ms) on 2-clause (~8-10s) real utterances."""
    proc = ContextProcessor({"active_tone_mode": "developer"})
    pause = np.zeros(int(0.35 * 16000), dtype=np.float32)

    valid_clips = []
    for item in en_items[:12]:
        p = _resolve_audio(EN_MANIFEST, item.get("audio_file", item["item_id"]), "en")
        if p:
            a, sr = sf.read(str(p), dtype="float32")
            if a.ndim > 1:
                a = np.mean(a, axis=1).astype(np.float32)
            if sr != 16000:
                a = resample_audio(a, int(sr), 16000)
            valid_clips.append((a, item["spoken_reference"]))

    post_stop_ms_list: List[float] = []
    wers: List[float] = []

    has_prefix_api = hasattr(stt_en, "build_pause_prefix_checkpoint") and hasattr(stt_en, "transcribe_with_checkpoint")

    for i in range(0, min(8, len(valid_clips) - 1)):
        (a1, ref1), (a2, ref2) = valid_clips[i], valid_clips[i + 1]
        combined = np.concatenate([a1, pause, a2]).astype(np.float32)
        combined_ref = f"{ref1} {ref2}"

        # Simulate background prefix checkpoint computed during the second clause while user is still speaking
        checkpoint = None
        if has_prefix_api:
            # At 75% through utterance (while user speaks clause 2), background worker checkpoints up to last pause
            partial_view = combined[: len(a1) + len(pause) + int(0.4 * 16000)]
            checkpoint = stt_en.build_pause_prefix_checkpoint(partial_view, language="en")

        # User releases hotkey NOW -> measure exact post-stop wall-clock time!
        t_stop = time.perf_counter()
        if checkpoint is not None and has_prefix_api:
            res = stt_en.transcribe_with_checkpoint(combined, checkpoint=checkpoint, language="en")
        else:
            res = stt_en.transcribe(combined, language="en")
        formatted = proc.process(res.get("text", ""), {"process_name": "code.exe"}, session_mode="developer", language="en")
        elapsed_ms = (time.perf_counter() - t_stop) * 1000.0

        post_stop_ms_list.append(elapsed_ms)
        wers.append(calculate_wer(combined_ref, formatted, "en"))

    return {
        "multi_clause_trials": len(post_stop_ms_list),
        "post_stop_p50_ms": _percentile(post_stop_ms_list, 50),
        "post_stop_p95_ms": _percentile(post_stop_ms_list, 95),
        "multi_clause_wer_pct": round(100.0 * statistics.mean(wers), 2) if wers else None,
        "wispr_flow_cloud_reference_p50_ms": "480-700 ms (cloud RTT + LLM)",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="current", help="Label for this benchmark snapshot")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path")
    args = parser.parse_args()

    print("=" * 76)
    print(f"  FLOWPILOT COMPETITIVE LEAPFROG BENCHMARK  [tag: {args.tag}]")
    print("=" * 76)

    raw_en = json.loads(EN_MANIFEST.read_text(encoding="utf-8")) if EN_MANIFEST.is_file() else []
    en_items = [x for x in raw_en if x.get("language") == "en"]
    stt_en = STTEngine({"local_model_size": "base", "cpu_threads": min(8, os.cpu_count() or 4)})
    stt_pl = STTEngine({"use_specialist_asr": False, "local_model_size": "small", "cpu_threads": min(8, os.cpu_count() or 4)})

    # Warm up models once so timing reflects warm interactive dictation
    if en_items:
        p0 = _resolve_audio(EN_MANIFEST, en_items[0].get("audio_file", en_items[0]["item_id"]), "en")
        if p0:
            stt_en.transcribe(p0.read_bytes(), language="en")
    ic = get_specialist_harness()
    if ic.is_available("ta"):
        ta_fix = PROJECT_ROOT / "tests" / "fixtures" / "ta-commonvoice-sample.wav"
        if ta_fix.is_file():
            ic.transcribe(ta_fix.read_bytes(), language="ta")

    t1 = run_track1_onset_capture(stt_en, en_items)
    print(f"[Track 1 | Early 650ms Speech Onset]   WER: {t1['early_onset_650ms_wer_pct']}%")

    t2 = run_track2_48khz_antialiasing(stt_en, en_items)
    print(f"[Track 2 | 48kHz HF Resampling]        Clean WER: {t2['clean_16khz_wer_pct']}% | 48kHz HF WER: {t2['48khz_hf_resampled_wer_pct']}% (Penalty: +{t2['aliasing_wer_penalty_pct']}%)")

    t3 = run_track3_multilingual(stt_pl)
    print(f"[Track 3 | Multilingual Real Voice]    Tamil CV WER: {t3['tamil_cv_wer_pct']}% ({t3['tamil_cv_cer_pct']}% CER) | Casual Tanglish WER: {t3['user_casual_tanglish_wer_pct']}% | Polish CV WER: {t3['polish_cv_wer_pct']}%")

    t4 = run_track4_context_and_self_correction()
    print(f"[Track 4 | Context & Self-Correction]  Pass Rate: {t4['exact_intent_and_symbol_pass_rate_pct']}% | Formatted WER: {t4['formatted_wer_pct']}%")

    t5 = run_track5_post_stop_latency(stt_en, en_items)
    print(f"[Track 5 | Multi-Clause Stop->Text]    P50: {t5['post_stop_p50_ms']} ms | P95: {t5['post_stop_p95_ms']} ms | WER: {t5['multi_clause_wer_pct']}%")

    summary = {
        "tag": args.tag,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "track1_onset_capture": t1,
        "track2_48khz_antialiasing": t2,
        "track3_multilingual": t3,
        "track4_context_and_self_correction": t4,
        "track5_post_stop_latency": t5,
    }

    out_path = args.output or (PROJECT_ROOT / "docs" / "evaluation" / f"COMPETITIVE_BENCHMARK_{args.tag}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved scoreboard -> {out_path}")


if __name__ == "__main__":
    main()
