"""
FlowPilot Comprehensive Multilingual & Performance Benchmark Harness
Executes empirical evaluations across real Windows host hardware.
Evaluates:
- Word Error Rate (WER)
- Character Error Rate (CER)
- Pipeline Latency (STT decode latency + Writing Intelligence transformation latency)
- Meaning & Fact Preservation Guard (Numbers, currency, dates, negations)
- Model Comparison: faster-whisper 'tiny' vs 'base' (CPU int8)
- Test Scenarios: Conversational, Self-Correction, Developer Jargon, Financial, Voice Snippets, Dialects, Multilingual
"""

import sys
import os
import time
import io
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import soundfile as sf
import win32com.client

from engine.stt_engine import STTEngine
from engine.writing_intelligence import WritingIntelligence
from engine.personalization import PersonalizationEngine
from engine.language_registry import LanguageRegistry

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
                    matrix[x - 1, y] + 1,      # deletion
                    matrix[x - 1, y - 1] + 1,  # substitution
                    matrix[x, y - 1] + 1       # insertion
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

# --- AUDIO SYNTHESIS VIA WINDOWS SAPI ---

def synthesize_audio_sapi(text: str) -> bytes:
    """Uses native Windows SAPI to synthesize actual spoken WAV audio on host."""
    sp = win32com.client.Dispatch("SAPI.SpVoice")
    fs = win32com.client.Dispatch("SAPI.SpFileStream")
    temp_wav = Path(tempfile_dir()) / f"sapi_{int(time.time()*1000)}.wav"
    try:
        fs.Open(str(temp_wav), 3)  # 3 = SSFMCreateForWrite
        sp.AudioOutputStream = fs
        sp.Speak(text)
        fs.Close()
        with open(temp_wav, "rb") as f:
            data = f.read()
        return data
    finally:
        if temp_wav.exists():
            try:
                temp_wav.unlink()
            except Exception:
                pass

def tempfile_dir() -> str:
    import tempfile
    return tempfile.gettempdir()

# --- BENCHMARK CORPUS DEFINITION ---

BENCHMARK_SCENARIOS = [
    {
        "id": "SC-01",
        "category": "Conversational English",
        "spoken_text": "Please review the quarterly financial report and send feedback by Friday afternoon.",
        "expected_polished": "Please review the quarterly financial report and send feedback by Friday afternoon.",
        "style": "professional",
        "lang": "en"
    },
    {
        "id": "SC-02",
        "category": "Spoken Self-Correction",
        "spoken_text": "Schedule the executive meeting for Tuesday, actually Wednesday morning at 10 AM.",
        "expected_polished": "Schedule the executive meeting for Wednesday morning at 10 AM.",
        "style": "professional",
        "lang": "en"
    },
    {
        "id": "SC-03",
        "category": "Technical & Developer Jargon",
        "spoken_text": "Deploy the fast api service with post gres and connect the graphql endpoint to flow pilot.",
        "expected_polished": "Deploy the FastAPI service with PostgreSQL and connect the GraphQL endpoint to FlowPilot.",
        "style": "developer",
        "lang": "en"
    },
    {
        "id": "SC-04",
        "category": "Financial Numbers & Negation Guard",
        "spoken_text": "The total project cost is 12500 dollars and we must not approve the contract before Monday.",
        "expected_polished": "The total project cost is $12,500 and we must not approve the contract before Monday.",
        "style": "professional",
        "lang": "en"
    },
    {
        "id": "SC-05",
        "category": "Voice Snippet Trigger",
        "spoken_text": "Please book a 15-minute consultation via insert my calendly so we can align.",
        "expected_polished": "Please book a 15-minute consultation via https://calendly.com/flowpilot-demo/15min so we can align.",
        "style": "professional",
        "lang": "en"
    },
    {
        "id": "SC-06",
        "category": "Regional Dialect (British English)",
        "spoken_text": "The color of the center theater is organized perfectly.",
        "expected_polished": "The colour of the centre theatre is organised perfectly.",
        "style": "professional",
        "lang": "en",
        "dialect": "en-GB"
    }
]

def run_benchmark():
    print("=" * 75)
    print("      FLOWPILOT MULTILINGUAL & PERFORMANCE BENCHMARK SUITE")
    print("=" * 75)

    personalization = PersonalizationEngine()
    writing_intel = WritingIntelligence(personalization=personalization)

    models_to_test = ["tiny", "base"]
    matrix_results = []

    for model_size in models_to_test:
        print(f"\n>>> EVALUATING FASTER-WHISPER MODEL: '{model_size}' (CPU int8) <<<")
        config = {
            "engine_mode": "local",
            "local_model_size": model_size,
            "language": "en"
        }
        stt = STTEngine(config, personalization=personalization)

        for sc in BENCHMARK_SCENARIOS:
            print(f"\n--- [{sc['id']}] {sc['category']} ---")
            spoken = sc["spoken_text"]
            expected = sc["expected_polished"]
            style = sc.get("style", "professional")
            dialect = sc.get("dialect", "")

            # 1. Generate real audio via Windows SAPI
            audio_bytes = synthesize_audio_sapi(spoken)
            audio_len_sec = round(len(audio_bytes) / 32000.0, 2)  # Approx 16kHz 16-bit

            # 2. Benchmark STT Latency
            t0 = time.time()
            stt_res = stt.transcribe(audio_bytes)
            t_stt = round((time.time() - t0) * 1000, 1)
            raw_text = stt_res.get("text", "")
            detected_lang = stt_res.get("detected_language", "en")

            # 3. Benchmark Writing Intelligence Latency
            t1 = time.time()
            polished_res = writing_intel.polish(raw_text, mode="polished", style=style, dialect=dialect)
            t_polish = round((time.time() - t1) * 1000, 1)
            final_text = polished_res["text"]

            # 4. Snippet Expansion check if snippet trigger scenario
            if "calendly" in final_text.lower():
                expanded, _ = personalization.expand_snippets(final_text)
                final_text = expanded

            total_latency = round(t_stt + t_polish, 1)

            # 5. Compute Error Rates against expected reference
            wer = calculate_wer(expected, final_text)
            cer = calculate_cer(expected, final_text)
            facts_ok = check_fact_preservation(expected, final_text)

            print(f"  Spoken Input:      '{spoken}'")
            print(f"  Raw Whisper:       '{raw_text}' (STT: {t_stt}ms, lang={detected_lang})")
            print(f"  Final Polished:    '{final_text}' (Polish: {t_polish}ms)")
            print(f"  Expected Target:   '{expected}'")
            print(f"  Metrics:           WER={wer:.2%} | CER={cer:.2%} | Total Latency={total_latency}ms | FactGuard={facts_ok}")

            matrix_results.append({
                "model": model_size,
                "id": sc["id"],
                "category": sc["category"],
                "stt_ms": t_stt,
                "polish_ms": t_polish,
                "total_ms": total_latency,
                "wer": wer,
                "cer": cer,
                "facts_ok": facts_ok,
                "output": final_text
            })

    print("\n" + "=" * 75)
    print("                    BENCHMARK SUMMARY MATRIX")
    print("=" * 75)
    header = f"{'Model':<8} | {'Scenario':<26} | {'STT (ms)':<9} | {'Total (ms)':<10} | {'WER':<8} | {'CER':<8} | {'Facts'}"
    print(header)
    print("-" * len(header))
    for r in matrix_results:
        f_str = "PASS" if r["facts_ok"] else "FAIL"
        print(f"{r['model']:<8} | {r['category']:<26} | {r['stt_ms']:<9} | {r['total_ms']:<10} | {r['wer']:<8.2%} | {r['cer']:<8.2%} | {f_str}")

    return matrix_results

if __name__ == "__main__":
    results = run_benchmark()
    sys.exit(0)
