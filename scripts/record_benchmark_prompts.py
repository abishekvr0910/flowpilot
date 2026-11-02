# -*- coding: utf-8 -*-
"""
scripts/record_benchmark_prompts.py

Interactive CLI tool for recording human speech evaluation clips for the
Tamil & Polish Multilingual Benchmark Corpus (docs/evaluation/TAMIL_POLISH_BENCHMARK_CORPUS.json).

Features:
- Reads prompts item-by-item from the benchmark manifest.
- Captures 16 kHz 16-bit mono PCM WAV via sounddevice (pure offline, local only).
- Saves recordings directly into `private/corpus/<lang>/<item_id>.wav`.
- Updates manifest item metadata with audio path, exact duration, and consent flag.
- Interactive controls:
  [Enter] Start / Stop recording
  [r]     Re-record current prompt
  [s]     Skip to next prompt
  [q]     Quit and save current progress
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Tuple

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
except ImportError as e:
    print(f"[ERROR] Required audio packages not found: {e}")
    print("Please ensure sounddevice and soundfile are installed in your environment.")
    sys.exit(1)


CORPUS_MANIFEST_PATH = PROJECT_ROOT / "docs" / "evaluation" / "TAMIL_POLISH_BENCHMARK_CORPUS.json"
PRIVATE_CORPUS_DIR = PROJECT_ROOT / "private" / "corpus"


def record_prompt_audio(sample_rate: int = 16000) -> Tuple[np.ndarray, float]:
    """Records audio from default input device until user presses Enter."""
    print("  [RECORDING] Speak now... (Press Enter when finished)")
    recorded_frames = []

    def callback(indata, frames, time_info, status):
        if status:
            print(f"Status warning: {status}", file=sys.stderr)
        recorded_frames.append(indata.copy())

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', callback=callback):
        input()

    if not recorded_frames:
        return np.array([], dtype='int16'), 0.0

    audio_data = np.concatenate(recorded_frames, axis=0)
    duration_sec = round(len(audio_data) / sample_rate, 3)
    return audio_data, duration_sec


def run_recording_session(language: str):
    if not CORPUS_MANIFEST_PATH.exists():
        print(f"[ERROR] Manifest not found at {CORPUS_MANIFEST_PATH}")
        sys.exit(1)

    with open(CORPUS_MANIFEST_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    lang_items = [it for it in corpus if it.get("language") == language]
    if not lang_items:
        print(f"[ERROR] No items found in manifest for language '{language}'. Available: 'ta', 'pl'")
        sys.exit(1)

    lang_dir = PRIVATE_CORPUS_DIR / language
    lang_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"   FLOWPILOT BENCHMARK RECORDING SESSION — LANGUAGE: {language.upper()}")
    print("=" * 70)
    print(f"Total prompts in session: {len(lang_items)}")
    print(f"Target directory: {lang_dir.resolve()}")
    print("\nInstructions:")
    print("  • Speak clearly at your natural dictation pace.")
    print("  • Controls: [Enter] to start, [Enter] again to finish, [r] re-record, [s] skip, [q] quit.\n")

    consent_accepted = False

    for idx, item in enumerate(lang_items, start=1):
        item_id = item["item_id"]
        spoken_ref = item["spoken_reference"]
        tanglish_ref = item.get("tanglish_reference", "")
        out_wav = lang_dir / f"{item_id}.wav"

        print("-" * 70)
        print(f"[{idx}/{len(lang_items)}] Item: {item_id} ({item.get('group', 'general')})")
        print(f"  TEXT:     {spoken_ref}")
        if tanglish_ref:
            print(f"  TANGLISH: {tanglish_ref}")
        if out_wav.exists():
            print(f"  (Existing recording found: {out_wav.name})")

        while True:
            cmd = input("\nPress [Enter] to record, 's' to skip, 'q' to quit: ").strip().lower()
            if cmd == 'q':
                print("\nSaving progress and exiting...")
                with open(CORPUS_MANIFEST_PATH, "w", encoding="utf-8") as f:
                    json.dump(corpus, f, indent=2, ensure_ascii=False)
                print(f"[SAVED] Manifest updated at {CORPUS_MANIFEST_PATH}")
                return
            if cmd == 's':
                print("Skipped.")
                break

            if not consent_accepted:
                confirm = input("Confirm recording consent for benchmark evaluation? (y/n): ").strip().lower()
                if confirm == 'y':
                    consent_accepted = True
                else:
                    print("Consent not given; skipping recording.")
                    break

            audio_data, duration = record_prompt_audio()
            if len(audio_data) < 16000 * 0.5:
                print("Recording too short (< 0.5s). Try again.")
                continue

            print(f"  Captured {duration}s of audio.")
            review = input("Accept recording? [Enter]=Yes, 'r'=Retry: ").strip().lower()
            if review == 'r':
                continue

            # Save WAV
            sf.write(str(out_wav), audio_data, 16000, subtype='PCM_16')
            print(f"  ✓ Saved to {out_wav}")

            # Update item in manifest
            rel_path = f"../../private/corpus/{language}/{out_wav.name}"
            item["audio_file"] = rel_path
            item["duration_sec"] = duration
            item["consent_verified"] = True
            break

    # Save final manifest
    with open(CORPUS_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)
    print("\n" + "=" * 70)
    print(f"SESSION COMPLETE: All recorded items saved into {lang_dir}")
    print(f"Updated manifest saved to {CORPUS_MANIFEST_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Record real-speech benchmark prompts for FlowPilot.")
    parser.add_argument("--lang", choices=["ta", "pl"], required=True, help="Language code ('ta' for Tamil, 'pl' for Polish)")
    args = parser.parse_args()
    run_recording_session(args.lang)
