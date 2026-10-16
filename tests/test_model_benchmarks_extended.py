"""
FlowPilot Extended Model Benchmark & Evaluation Suite
Empirically compares local ASR models across challenging conditions:
1. Clean conversational speech
2. Fast speech pacing (accelerated SAPI rate)
3. Degraded audio with synthetic background noise (SNR ~15 dB)
4. Heavy developer / technical terms
5. Complex spoken self-corrections with negations
6. Financial figures and critical negation retention

Measures:
- Latency (STT decode ms + Polish ms)
- Real-Time Factor (RTF)
- Word Error Rate (WER)
- Character Error Rate (CER)
- FactGuard Preservation
- Memory footprint (RAM RSS MB)
"""

import sys
import os
import time
import io
import re
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import soundfile as sf
import psutil
import win32com.client

from engine.stt_engine import STTEngine
from engine.writing_intelligence import WritingIntelligence
from engine.personalization import PersonalizationEngine

# --- LEVENSHTEIN METRICS ---

def compute_levenshtein(seq1: List[str], seq2: List[str]) -> int:
    size_x = len(seq1) + 1
    size_y = len(seq2) + 1
    matrix = np.zeros((size_x, size_y), dtype=int)
    for x in range(size_x):
        matrix[x, 0] = x
    for y in range(size_y):
        matrix[0, y] = y

    for x in range(1, size_x):
        for y in range(1, size_y):
            if seq1[x - 1] == seq2[y - 1]:
                matrix[x, y] = matrix[x - 1, y - 1]
            else:
                matrix[x, y] = min(
                    matrix[x - 1, y] + 1,
                    matrix[x - 1, y - 1] + 1,
                    matrix[x, y - 1] + 1
                )
    return int(matrix[size_x - 1, size_y - 1])

def calculate_wer(reference: str, hypothesis: str) -> float:
    ref_tokens = re.findall(r"\b\w+\b", reference.lower())
    hyp_tokens = re.findall(r"\b\w+\b", hypothesis.lower())
    if not ref_tokens:
        return 0.0 if not hyp_tokens else 1.0
    dist = compute_levenshtein(ref_tokens, hyp_tokens)
    return round(float(dist) / len(ref_tokens), 4)

def calculate_cer(reference: str, hypothesis: str) -> float:
    ref_chars = list(re.sub(r"\s+", "", reference.lower()))
    hyp_chars = list(re.sub(r"\s+", "", hypothesis.lower()))
    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0
    dist = compute_levenshtein(ref_chars, hyp_chars)
    return round(float(dist) / len(ref_chars), 4)

def check_fact_preservation(reference: str, hypothesis: str) -> bool:
    """Verifies that numbers, currency, and critical negations in reference are retained in hypothesis."""
    ref_nums = [re.sub(r"[^\d]", "", n) for n in re.findall(r"\$?\d+(?:,\d+)*(?:\.\d+)?", reference)]
    hyp_nums = [re.sub(r"[^\d]", "", n) for n in re.findall(r"\$?\d+(?:,\d+)*(?:\.\d+)?", hypothesis)]
    for num in ref_nums:
        if num and num not in hyp_nums:
            return False

    negations = ["not", "never", "no", "cannot", "won't", "don't"]
    for neg in negations:
        if re.search(r"\b" + neg + r"\b", reference.lower()):
            if not re.search(r"\b" + neg + r"\b", hypothesis.lower()):
                return False
    return True

# --- AUDIO SYNTHESIS & DEGRADATION ---

def synthesize_audio(text: str, rate: int = 0) -> Tuple[np.ndarray, int]:
    """Synthesizes speech using Windows SAPI at a specified speech rate."""
    sp = win32com.client.Dispatch("SAPI.SpVoice")
    sp.Rate = rate  # -10 to +10
    fs = win32com.client.Dispatch("SAPI.SpFileStream")
    temp_path = Path(tempfile.gettempdir()) / f"sapi_bench_{int(time.time()*1000)}.wav"
    try:
        fs.Open(str(temp_path), 3)
        sp.AudioOutputStream = fs
        sp.Speak(text)
        fs.Close()
        data, sample_rate = sf.read(str(temp_path), dtype="float32")
        if data.ndim > 1:
            data = data[:, 0]
        return data, sample_rate
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass

def add_acoustic_noise(audio: np.ndarray, snr_db: float = 15.0) -> np.ndarray:
    """Adds white acoustic noise at a specified Signal-to-Noise Ratio (SNR)."""
    signal_power = np.mean(audio ** 2)
    if signal_power == 0:
        return audio
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise = np.random.normal(0, np.sqrt(noise_power), len(audio)).astype(np.float32)
    noisy_audio = audio + noise
    # Normalize to prevent clipping
    max_val = np.max(np.abs(noisy_audio))
    if max_val > 1.0:
        noisy_audio = noisy_audio / max_val
    return noisy_audio

# --- BENCHMARK SCENARIOS ---

TEST_SCENARIOS = [
    {
        "id": "T1-Conversational",
        "name": "Conversational Business (Clean)",
        "text": "Please review the quarterly financial report and send your feedback before Friday.",
        "expected": "Please review the quarterly financial report and send your feedback before Friday.",
        "rate": 0,
        "noisy": False,
        "style": "professional"
    },
    {
        "id": "T2-FastPaced",
        "name": "Fast-Paced Dictation (Rate +3)",
        "text": "We need to immediately confirm the deployment schedule with the infrastructure lead.",
        "expected": "We need to immediately confirm the deployment schedule with the infrastructure lead.",
        "rate": 3,
        "noisy": False,
        "style": "professional"
    },
    {
        "id": "T3-NoisyAcoustic",
        "name": "Acoustic Noise Degraded (15dB SNR)",
        "text": "The client requested an updated timeline for the mobile application release.",
        "expected": "The client requested an updated timeline for the mobile application release.",
        "rate": 0,
        "noisy": True,
        "style": "professional"
    },
    {
        "id": "T4-DeveloperJargon",
        "name": "Developer Jargon & Phonetic Biasing",
        "text": "Deploy the fast api microservice with post gres and connect the graphql endpoint to flow pilot.",
        "expected": "Deploy the FastAPI microservice with PostgreSQL and connect the GraphQL endpoint to FlowPilot.",
        "rate": 0,
        "noisy": False,
        "style": "developer"
    },
    {
        "id": "T5-ComplexCorrection",
        "name": "Spoken Self-Correction & Negation",
        "text": "The server migration should occur on Tuesday -- actually, Wednesday morning at 10 AM.",
        "expected": "The server migration should occur on Wednesday morning at 10 AM.",
        "rate": 0,
        "noisy": False,
        "style": "professional"
    },
    {
        "id": "T6-FinancialNegation",
        "name": "Financial Numbers & Critical Negation",
        "text": "The total budget is 12500 dollars and we must not exceed the approved limit.",
        "expected": "The total budget is $12,500 and we must not exceed the approved limit.",
        "rate": 0,
        "noisy": False,
        "style": "professional"
    }
]

def run_model_benchmark():
    print("=" * 80)
    print("      FLOWPILOT EXTENDED SPEECH MODEL BENCHMARK & EVALUATION")
    print("=" * 80)
    
    models_to_test = ["tiny", "base"]
    results = []
    
    pers = PersonalizationEngine()
    wi = WritingIntelligence()
    
    for model_name in models_to_test:
        print(f"\n>>> EVALUATING MODEL: faster-whisper '{model_name}' (CPU INT8) <<<")
        config = {"engine_mode": "local", "local_model_size": model_name, "language": "en"}
        stt = STTEngine(config=config, personalization=pers)
        
        # Warmup and memory baseline
        try:
            stt._get_local_model()
        except Exception as e:
            print(f"  [Notice] Model '{model_name}' could not be loaded offline: {e}. Skipping benchmark for this model.")
            continue
        process = psutil.Process()
        baseline_ram = process.memory_info().rss / (1024 * 1024)
        print(f"  Loaded model '{model_name}'. Baseline Process RAM: {baseline_ram:.2f} MB")
        
        for sc in TEST_SCENARIOS:
            # 1. Synthesize audio
            audio, sr = synthesize_audio(sc["text"], rate=sc["rate"])
            duration = len(audio) / sr
            
            if sc["noisy"]:
                audio = add_acoustic_noise(audio, snr_db=15.0)
                
            # Convert to 16kHz WAV buffer
            wav_buf = io.BytesIO()
            sf.write(wav_buf, audio, sr, format="WAV", subtype="PCM_16")
            wav_bytes = wav_buf.getvalue()
            
            # 2. Benchmark STT Decode Latency
            t0 = time.perf_counter()
            res = stt.transcribe(wav_bytes)
            stt_latency = (time.perf_counter() - t0) * 1000.0
            raw_text = res["text"]
            lang = res.get("detected_language", "en")
            
            # 3. Benchmark Writing Intelligence Polish Latency
            t1 = time.perf_counter()
            polished_res = wi.polish(raw_text, mode="polished", style=sc["style"])
            polish_latency = (time.perf_counter() - t1) * 1000.0
            polished = polished_res["text"]
            
            total_latency = stt_latency + polish_latency
            rtf = (total_latency / 1000.0) / duration if duration > 0 else 0
            
            # 4. Accuracy Metrics
            wer = calculate_wer(sc["expected"], polished)
            cer = calculate_cer(sc["expected"], polished)
            
            # 5. FactGuard Verification
            fact_guard_ok = check_fact_preservation(sc["expected"], polished)
            
            current_ram = process.memory_info().rss / (1024 * 1024)
            
            print(f"\n  [{sc['id']}] {sc['name']}")
            print(f"    Raw STT:     '{raw_text}'")
            print(f"    Polished:    '{polished}'")
            print(f"    Target:      '{sc['expected']}'")
            print(f"    STT Latency: {stt_latency:.1f}ms | Polish: {polish_latency:.1f}ms | Total: {total_latency:.1f}ms (RTF: {rtf:.2f}x)")
            print(f"    Metrics:     WER={wer*100:.1f}% | CER={cer*100:.1f}% | FactGuard={'PASS' if fact_guard_ok else 'FAIL'}")
            
            results.append({
                "model": model_name,
                "id": sc["id"],
                "name": sc["name"],
                "duration": duration,
                "stt_ms": stt_latency,
                "polish_ms": polish_latency,
                "total_ms": total_latency,
                "rtf": rtf,
                "wer": wer * 100,
                "cer": cer * 100,
                "fact_guard": fact_guard_ok,
                "ram_mb": current_ram
            })
            
    print("\n" + "=" * 80)
    print("                     BENCHMARK SUMMARY MATRIX")
    print("=" * 80)
    print(f"{'Model':<6} | {'Scenario':<25} | {'Duration':<7} | {'STT(ms)':<8} | {'Total':<7} | {'RTF':<5} | {'WER':<6} | {'CER':<6} | {'Facts'}")
    print("-" * 80)
    for r in results:
        print(f"{r['model']:<6} | {r['name'][:25]:<25} | {r['duration']:<5.1f}s  | {r['stt_ms']:<8.1f} | {r['total_ms']:<7.1f} | {r['rtf']:<5.2f} | {r['wer']:<5.1f}% | {r['cer']:<5.1f}% | {'PASS' if r['fact_guard'] else 'FAIL'}")
    print("=" * 80)
    if not results:
        print("FAILED: No models could be evaluated.")
        return False
    return True

if __name__ == "__main__":
    success = run_model_benchmark()
    sys.exit(0 if success else 1)
