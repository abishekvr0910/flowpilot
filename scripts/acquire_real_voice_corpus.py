"""
FlowPilot Real-Voice Corpus Acquisition (Common Voice 17.0)
=========================================================
Builds a consented real-human-speech evaluation corpus for German (de),
Spanish (es) and French (fr) so that the language claims can be measured
against real acoustic conditions instead of synthetic TTS.

Source
------
Mozilla Common Voice 17.0, mirrored on the Hugging Face Hub as
``fixie-ai/common_voice_17_0`` (dataset ``mozilla-foundation/common_voice_17_0``).
Common Voice clips are published by Mozilla under CC0, and every contributor
consented to publication at recording time. Only the ``validation`` split is
read; one Parquet row group is fetched at a time over HTTP range requests, so
the full multi-gigabyte language shards are never downloaded.

Outputs
-------
* ``private/corpus/<lang>/*.wav`` - 16 kHz mono PCM16 WAV (gitignored)
* ``docs/evaluation/DE_ES_FR_REAL_VOICE_MANIFEST.json`` - manifest metadata
  (gitignored audio, committed metadata)

The script performs NO evaluation. Measurement is done separately by
``benchmarks/run_real_voice_eval.py`` against the offline model, so the
measurement path itself stays network-free.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import fsspec
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_ROOT = PROJECT_ROOT / "private" / "corpus"
MANIFEST_PATH = PROJECT_ROOT / "docs" / "evaluation" / "DE_ES_FR_REAL_VOICE_MANIFEST.json"

REPO = "https://huggingface.co/datasets/fixie-ai/common_voice_17_0/resolve/main"
FFMPEG = r"S:\tools\ffmpeg\bin\ffmpeg.exe"

LANGUAGES = ("de", "es", "fr")
TARGET_PER_LANGUAGE = 40
# Half the sample must carry a critical entity (a negation or a number), so
# the fact-retention gate is actually exercised rather than measuring an
# empty set. The other half is plain declarative speech.
ENTITY_TARGET_PER_LANGUAGE = 20
SAMPLE_RATE = 16000

# Quality filters. down_votes == 0 keeps out clips the community rejected.
MIN_UP_VOTES = 2
MAX_DOWN_VOTES = 0
MIN_SENTENCE_CHARS = 15
MAX_SENTENCE_CHARS = 200

NUMBER_RE = re.compile(r"\d")
NEGATIONS = {
    "de": {"nicht", "kein", "keine", "keinen", "keinem", "keiner", "keines",
           "nie", "niemals", "nichts", "niemand", "ohne", "weder"},
    "es": {"no", "nunca", "jamás", "nadie", "nada", "ninguno", "ninguna",
           "sin", "tampoco"},
    "fr": {"ne", "pas", "jamais", "rien", "personne", "aucun", "aucune",
           "sans", "plus", "ni"},
}

CODE_TOKENS = {
    "docker", "kubernetes", "python", "javascript", "typescript", "react",
    "fastapi", "postgresql", "redis", "nginx", "api", "url", "http", "json",
    "sql", "git", "linux", "server", "client", "function", "variable",
    "endpoint", "token", "python", "npm", "curl", "script", "code",
}


def _decode_to_wav(mp3_bytes: bytes, out_path: Path) -> float:
    """Decode MP3 bytes to 16 kHz mono PCM16 WAV. Returns duration in seconds."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # ffmpeg is invoked through a file path rather than stdin: passing
    # encoding="utf-8" puts the subprocess in text mode, which cannot accept
    # the binary MP3 payload on stdin.
    tmp_mp3 = out_path.with_suffix(".mp3.tmp")
    tmp_mp3.write_bytes(mp3_bytes)
    try:
        proc = subprocess.run(
            [
                FFMPEG, "-hide_banner", "-loglevel", "error",
                "-i", str(tmp_mp3),
                "-ar", str(SAMPLE_RATE),
                "-ac", "1",
                "-acodec", "pcm_s16le",
                "-f", "wav",
                str(out_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    finally:
        tmp_mp3.unlink(missing_ok=True)
    if proc.returncode != 0 or not out_path.is_file():
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[:200]}")
    return out_path.stat().st_size / (SAMPLE_RATE * 2)


def _critical_entities(sentence: str, language: str) -> list:
    """Numbers and negations that must survive transcription."""
    entities = []
    for token in re.findall(r"\d+(?:[.,]\d+)?", sentence):
        entities.append(token)
    words = set(re.findall(r"[\w']+", sentence.lower()))
    entities.extend(sorted(words & NEGATIONS.get(language, set())))
    return entities


def _has_critical_entity(sentence: str, language: str) -> bool:
    """True when the sentence carries a negation or a number worth guarding."""
    return bool(_critical_entities(sentence, language))


def _group_for(sentence: str) -> str:
    lowered = sentence.lower()
    if NUMBER_RE.search(sentence):
        return "quantities"
    if any(token in lowered for token in CODE_TOKENS):
        return "developer_code"
    return "clean"


def acquire_language(language: str, fs, target: int) -> list:
    """Collect ``target`` consented clips for one language.

    Clips are bucketed: ``entity_target`` of them must carry a negation or a
    number so the critical-entity gate has real coverage, the rest are plain
    declarative speech.
    """
    path = f"{REPO}/{language}/validation-00000-of-00008.parquet"
    entity_target = min(ENTITY_TARGET_PER_LANGUAGE, target)
    plain_target = target - entity_target
    entity_items: list = []
    plain_items: list = []
    seen_sentences = set()

    with fs.open(path, "rb") as handle:
        parquet = pq.ParquetFile(handle)
        for group_index in range(parquet.metadata.num_row_groups):
            if len(entity_items) >= entity_target and len(plain_items) >= plain_target:
                break
            table = parquet.read_row_group(group_index)
            for row in table.to_pylist():
                if len(entity_items) >= entity_target and len(plain_items) >= plain_target:
                    break
                sentence = (row.get("sentence") or "").strip()
                if not sentence or sentence in seen_sentences:
                    continue
                if not (MIN_SENTENCE_CHARS <= len(sentence) <= MAX_SENTENCE_CHARS):
                    continue
                if (row.get("down_votes") or 0) > MAX_DOWN_VOTES:
                    continue
                if (row.get("up_votes") or 0) < MIN_UP_VOTES:
                    continue
                if row.get("locale") != language:
                    continue
                audio = row.get("audio") or {}
                blob = audio.get("bytes")
                if not blob:
                    continue

                wants_entity = _has_critical_entity(sentence, language)
                if wants_entity and len(entity_items) >= entity_target:
                    continue
                if not wants_entity and len(plain_items) >= plain_target:
                    continue

                seen_sentences.add(sentence)
                bucket = entity_items if wants_entity else plain_items
                item_id = f"{language}-cv-{len(entity_items) + len(plain_items) + 1:03d}"
                wav_path = CORPUS_ROOT / language / f"{item_id}.wav"
                try:
                    duration = _decode_to_wav(blob, wav_path)
                except Exception as exc:  # noqa: BLE001 - one bad clip must not stop the run
                    print(f"    skip {item_id}: {exc}")
                    continue

                bucket.append({
                    "item_id": item_id,
                    "language": language,
                    "group": _group_for(sentence),
                    "spoken_reference": sentence,
                    # Common Voice sentences are already punctuated and
                    # capitalised, so the formatted reference is the sentence
                    # itself. This makes Formatted Quality Score a measure of
                    # content preservation through the formatter.
                    "formatted_reference": sentence,
                    # Speaker identity is anonymised: the corpus carries no
                    # per-contributor identifiers.
                    "speaker_id": f"cv-anon-{language}",
                    "consent_verified": True,
                    "audio_file": os.path.relpath(wav_path, MANIFEST_PATH.parent).replace("\\", "/"),
                    "duration_sec": round(duration, 3),
                    "critical_entities": _critical_entities(sentence, language),
                })
                tag = "crit" if wants_entity else "    "
                print(f"    + {item_id} [{tag}] {duration:5.2f}s  {sentence[:60]}")
    return entity_items + plain_items


def main() -> int:
    print("=" * 72)
    print("  FLOWPILOT REAL-VOICE CORPUS ACQUISITION — Common Voice 17.0 (CC0)")
    print("=" * 72)
    fs = fsspec.filesystem("http")
    all_items = []
    for language in LANGUAGES:
        print(f"\n[{language}] collecting up to {TARGET_PER_LANGUAGE} consented clips...")
        items = acquire_language(language, fs, TARGET_PER_LANGUAGE)
        print(f"[{language}] collected {len(items)}")
        all_items.extend(items)

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(all_items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    total_audio = sum(
        (CORPUS_ROOT / it["language"] / (it["item_id"] + ".wav")).stat().st_size
        for it in all_items
        if (CORPUS_ROOT / it["language"] / (it["item_id"] + ".wav")).is_file()
    )
    print("\n" + "=" * 72)
    print(f"  manifest : {MANIFEST_PATH}")
    print(f"  items    : {len(all_items)}")
    print(f"  audio    : {round(total_audio / 1048576, 1)} MB in {CORPUS_ROOT}")
    print("  Audio stays under private/corpus/ which is gitignored.")
    print("=" * 72)
    return 0 if all_items else 1


if __name__ == "__main__":
    sys.exit(main())
