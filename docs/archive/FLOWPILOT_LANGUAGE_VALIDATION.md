# Archived multilingual validation — corrected notice

This October 2026 report was withdrawn on 2026-10-22 because it mislabeled
deterministic script/formatting checks as speech-recognition accuracy. Its
"0.00% WER/CER" and "production-ready" language ratings are **not valid
evidence** of multilingual dictation accuracy. The original version remains
available in Git history for provenance, but must not be quoted in product,
pilot, investment, or compliance materials.

The related test, `tests/test_multilingual_validation.py`, synthesizes audio
with Windows SAPI and also checks writing transformations. A passing test
shows only that those controlled checks passed; it does not measure real
human voices, accents, background noise, microphone routing, or end-to-end
paste reliability.

The [v3.0.2 release audit](../release/FLOWPILOT_V302_RELEASE_REPORT.md)
reports **raw** WER on its small synthetic SAPI multilingual subset of
95.24% for German (2 cases, 21 reference words), 61.54% for Spanish
(2 cases, 26 words), and 63.64% for French (2 cases, 22 words). These are
concerning results, but the samples are too small and synthetic to estimate
production accuracy. That report's 12.01% strict cleaned WER and 10.84%
normalized WER are **mixed-category aggregate** figures, not English-only
or real-voice benchmarks. Its 0.00% negation WER covers one 47-word
safety-critical subset, not all languages or all facts.

Until a consented human-voice corpus is evaluated per language and model,
FlowPilot should describe language options as available or experimental,
not validated or production-ready. Prefer
[`REAL_VOICE_CORPUS_SCHEMA.md`](../evaluation/REAL_VOICE_CORPUS_SCHEMA.md)
for the evaluation protocol and publish per-language denominators, confidence
intervals, hardware/model settings, and error examples with future results.
