# English and Indic real speech check, 26 October 2026

This is a development diagnostic, not a language quality certification. Audio came from the validation split of Mozilla Common Voice 17.0, via the `fixie-ai/common_voice_17_0` mirror at revision `34f78a43893414e7b6e271ba94c1d5e05f18b239`. The [manifest](EN_HI_TA_ML_REAL_VOICE_MANIFEST.json) contains reference text and relative local audio paths; the 16 kHz WAV files remain under ignored `private/corpus/`. No contributor identifiers were stored. Common Voice publishes contributed recordings under CC0. The mirror layout was checked on 26 October 2026.

The acquisition script selected clips with at least two upvotes, no downvotes, and reference sentences 15 to 200 characters long. Its target was ten clips per language with half containing a number or negation. The available validation shards met that target for English and Hindi, but supplied only five eligible clips each for Tamil and Malayalam under these filters. Those smaller samples are especially weak evidence. The sentences are mostly general speech; they do not measure developer vocabulary, code switching, microphone noise, or individual pilot speakers.

| Language | Clips | Base mean WER | Small mean WER | Base mean decode | Small mean decode |
|---|---:|---:|---:|---:|---:|
| English | 10 | 14.3% | 12.4% | 0.63 s | 2.09 s |
| Hindi | 10 | 103.4% | 73.6% | 0.77 s | 2.58 s |
| Tamil | 5 | 76.1% | 68.7% | 0.76 s | 2.42 s |
| Malayalam | 5 | 100.0% | 100.0% | 1.00 s | 2.81 s |

These are means of per-clip raw WER values against Common Voice references. WER can exceed 100% when the recognizer inserts extra words. The table uses the **same 30 clips** for both models after a deterministic decoder change. The base model file SHA-256 is `d01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9`; the small model file SHA-256 is `3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671`. Both used CPU int8 with eight threads. These decode times exclude microphone capture, formatting, OS insertion, and visible delivery. The evaluator did not instrument network traffic; runtime model loading used local weights.

Before the decoder change, Faster-Whisper's default temperature retry sequence took a mean 70.88 seconds on the five Malayalam clips with the small model, with no correct transcript. Setting one deterministic temperature and a duration-based output token cap reduced that mean to 2.81 seconds on the same clips. Across all 30 small-model clips, warm processing p95 fell from 71.90 to 3.05 seconds. Accuracy remained poor: Hindi WER changed from 72.1% to 73.6%; English, Tamil, and Malayalam WER were unchanged. The latency repair is not an accuracy repair.

**Product decision:** Hindi, Tamil, and Malayalam remain experimental in the language picker and setup guidance. Do not describe them as pilot-ready or use this small sample to claim parity with another product. The immediate next evaluation needs consented target-user recordings, multiple speakers per language, developer terms, mixed English and local-language speech, and explicit acceptance thresholds. Malayalam also needs a different local model or another validated recognition path before it can be offered as reliable dictation.

Reproduce the current source evaluation after acquiring the audio:

```powershell
python -X utf8 scripts/acquire_real_voice_corpus.py --languages en hi ta ml --target-per-language 10 --manifest docs/evaluation/EN_HI_TA_ML_REAL_VOICE_MANIFEST.json
python -X utf8 benchmarks/run_real_voice_eval.py --manifest docs/evaluation/EN_HI_TA_ML_REAL_VOICE_MANIFEST.json --model base --output scratch/evaluation/EN_HI_TA_ML_BASE_BOUNDED.json
python -X utf8 benchmarks/run_real_voice_eval.py --manifest docs/evaluation/EN_HI_TA_ML_REAL_VOICE_MANIFEST.json --model small --output scratch/evaluation/EN_HI_TA_ML_SMALL_BOUNDED.json
```

The acquisition command intentionally exits with code 2 if any language falls short of its requested count, while preserving the partial manifest for inspection. Acquisition uses HTTPS; evaluation and production dictation use local files.
