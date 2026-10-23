"""
Tests for Multilingual Evaluation Metrics & Real-Voice Corpus Schema (PR 2)
"""

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.evaluation_metrics import (
    normalize_unicode,
    tokenize_multilingual,
    calculate_wer,
    calculate_cer,
    verify_critical_facts,
    calculate_formatted_quality_score,
)
from engine.real_voice_corpus import RealVoiceCorpus, CorpusItem, get_dev_smoke_corpus

def test_unicode_normalization_preserves_indic_marks():
    """Confirms Unicode normalization retains Indic combining characters (virama, matras)."""
    # Tamil: தமிழ் (த + ம + ி + ழ + ்)
    ta = "தமிழ்"
    norm_ta = normalize_unicode(ta)
    assert norm_ta == ta
    assert len(norm_ta) == 5

    # Malayalam: മലയാളം (മ + ല + യ + ാ + ള + ം)
    ml = "മലയാളം"
    norm_ml = normalize_unicode(ml)
    assert norm_ml == ml
    assert len(norm_ml) == 6

    # Hindi: हिन्दी (ह + ि + न + ् + द + ी)
    hi = "हिन्दी"
    norm_hi = normalize_unicode(hi)
    assert norm_hi == hi

def test_wer_calculation_multilingual():
    """Tests WER across English, Hindi, Tamil, and Malayalam with exact, substitution, and deletion."""
    # 1. Exact match -> WER 0.0
    assert calculate_wer("the meeting is on monday", "the meeting is on monday", "en") == 0.0
    assert calculate_wer("இன்றைய பணிகள் முடிந்துவிட்டன", "இன்றைய பணிகள் முடிந்துவிட்டன", "ta") == 0.0
    assert calculate_wer("आज का काम पूरा हुआ", "आज का काम पूरा हुआ", "hi") == 0.0
    assert calculate_wer("ഇന്നത്തെ ജോലികൾ കഴിഞ്ഞു", "ഇന്നത്തെ ജോലികൾ കഴിഞ്ഞു", "ml") == 0.0

    # 2. Single substitution in 4-word phrase -> WER 0.25
    wer_sub = calculate_wer("the meeting is monday", "the meeting is friday", "en")
    assert wer_sub == 0.25

    # 3. Single deletion in 4-word phrase -> WER 0.25
    wer_del = calculate_wer("the meeting is monday", "the meeting is", "en")
    assert wer_del == 0.25

    # 4. Indic substitution
    wer_hi = calculate_wer("आज काम पूरा हुआ", "आज काम अधूरा हुआ", "hi")
    assert wer_hi == 0.25

def test_cer_calculation_preserves_indic_codepoints():
    """CER retains Indic codepoints without naive ASCII character stripping."""
    ref = "தமிழ்"
    hyp_exact = "தமிழ்"
    assert calculate_cer(ref, hyp_exact, "ta") == 0.0

    # Typo: change one character
    hyp_typo = "தமிழா"
    cer = calculate_cer(ref, hyp_typo, "ta")
    assert 0.0 < cer < 0.5

def test_critical_facts_verification_numbers_negations_and_code():
    """Strictly catches altered numbers, missing negations, and lost code identifiers."""
    # 1. Number mismatch
    ref1 = "Deploy version 3.1.0 with 25 instances"
    hyp1 = "Deploy version 3.2.0 with 25 instances"
    res1 = verify_critical_facts(ref1, hyp1, "en")
    assert res1["preserved"] is False
    assert "3.1.0" in res1["missing_numbers"] or "3.1.0" not in hyp1

    # 2. Negation lost
    ref2 = "We did not push the binary release"
    hyp2 = "We did push the binary release"
    res2 = verify_critical_facts(ref2, hyp2, "en")
    assert res2["preserved"] is False
    assert "not" in res2["missing_negations"]

    # 3. Code identifier lost
    ref3 = "Review parse_hotkey_string in hotkey_service.py"
    hyp3 = "Review parse hotkey string in hotkey service"
    res3 = verify_critical_facts(ref3, hyp3, "en")
    assert res3["preserved"] is False
    assert "parse_hotkey_string" in res3["missing_identifiers"]

    # 4. Indic negation lost (Hindi)
    ref4 = "यह फ़ाइल सर्वर पर नहीं भेजी जाएगी"
    hyp4 = "यह फ़ाइल सर्वर पर भेजी जाएगी"
    res4 = verify_critical_facts(ref4, hyp4, "hi")
    assert res4["preserved"] is False
    assert "नहीं" in res4["missing_negations"]

def test_formatted_quality_score():
    """Formatted quality score awards 1.0 for perfect desired writing and penalizes divergences."""
    desired = "The meeting is scheduled for next Monday at 9:30."
    assert calculate_formatted_quality_score(desired, "The meeting is scheduled for next Monday at 9:30.", "en") == 1.0

    # Raw spoken transcript lacking punctuation/capitalization gets lower quality score
    raw = "the meeting is scheduled for next monday at nine thirty"
    score = calculate_formatted_quality_score(desired, raw, "en")
    assert 0.0 < score < 1.0

def test_dev_smoke_corpus_manifest_integrity():
    """Validates the 40 development smoke utterances schema and integrity."""
    corpus = get_dev_smoke_corpus()
    assert len(corpus.items) == 40

    # Exactly 10 per priority language
    assert len(corpus.filter_by_language("en")) == 10
    assert len(corpus.filter_by_language("hi")) == 10
    assert len(corpus.filter_by_language("ta")) == 10
    assert len(corpus.filter_by_language("ml")) == 10

    # Validate integrity rules
    ok, errors = corpus.validate_integrity()
    assert ok is True, f"Manifest integrity failed: {errors}"

    # JSON save and load round-trip
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "manifest.json"
        corpus.save_manifest(p)
        loaded = RealVoiceCorpus.load_manifest(p)
        assert len(loaded.items) == 40
        assert loaded.items[0].item_id == "en-01-clean"
        assert loaded.items[20].language == "ta"


def test_runtime_summary_keeps_unmeasured_delivery_unknown():
    from benchmarks.runtime_metrics import percentile, summarize_processing_trials
    trials = [
        {"status": "evaluated", "phase": "cold", "decode_sec": 2.0, "format_sec": 0.1},
        {"status": "evaluated", "phase": "warm", "decode_sec": 0.2, "format_sec": 0.1},
        {"status": "evaluated", "phase": "warm", "decode_sec": 0.4, "format_sec": 0.1},
        {"status": "failed", "phase": "warm", "decode_sec": None, "format_sec": None},
    ]
    summary = summarize_processing_trials(trials)
    assert summary["cold"]["processing_p50_sec"] == 2.1
    assert summary["warm"]["count"] == 2
    assert summary["warm"]["processing_p50_sec"] == 0.4
    assert summary["warm"]["processing_p95_sec"] == 0.49
    assert summary["stop_to_visible_text"]["status"] == "not_measured"
    assert summary["stop_to_visible_text"]["p95_sec"] is None
    assert percentile([], 95) is None
    for invalid in (float("nan"), float("inf"), -1):
        try:
            percentile([invalid], 95)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid timing was accepted")

if __name__ == "__main__":
    print("Running Multilingual Evaluation Metrics tests...")
    test_unicode_normalization_preserves_indic_marks()
    test_wer_calculation_multilingual()
    test_cer_calculation_preserves_indic_codepoints()
    test_critical_facts_verification_numbers_negations_and_code()
    test_formatted_quality_score()
    test_dev_smoke_corpus_manifest_integrity()
    test_runtime_summary_keeps_unmeasured_delivery_unknown()
    print("[RESULT] Multilingual Evaluation Metrics tests PASSED.")
    sys.exit(0)
