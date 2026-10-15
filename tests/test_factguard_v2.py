"""
FlowPilot FactGuard v2 Regression Test Suite
Validates structured entity extraction, transformation classes,
CLI flags preservation, unit-corruption prevention, soundalike protection,
file path safety, and user dictionary preservation.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.writing_intelligence import FactGuard, TransformationClass, WritingIntelligence

def test_structured_entity_extraction():
    print("=" * 65)
    print("TEST: FACTGUARD V2 STRUCTURED ENTITY EXTRACTION")
    print("=" * 65)

    sample = (
        "Do not run pytest -v --dry-run without config_prod.json on 1450 units. "
        "Visit https://github.com/flowpilot with fifteen items."
    )
    entities = FactGuard.extract_protected_entities(sample, custom_terms=["FlowPilot"])

    assert "not" in entities["negations"]
    assert "without" in entities["negations"]
    assert "--dry-run" in entities["cli_flags"]
    assert "-v" in entities["cli_flags"]
    assert "config_prod.json" in entities["file_paths"]
    assert any("https://github.com/flowpilot" in u for u in entities["urls"])
    assert ("1450", "units") in entities["units"]
    assert entities["spoken_nums"].get("fifteen") == "15"
    assert "FlowPilot" in entities["custom_terms"]
    print("[PASS] Structured entity extraction successfully captured all protected tokens.")


def test_unit_currency_corruption_guard():
    print("\n" + "=" * 65)
    print("TEST: UNIT CURRENCY PREPEND CORRUPTION GUARD")
    print("=" * 65)

    # Simulates Whisper/polisher adding '$' to non-currency unit '1450 units' (ND-01 audit issue)
    raw = "The batch size is 1450 units for the benchmark"
    bad_polished = "The batch size is $1,450 units for the benchmark."

    final_text, is_safe, warnings = FactGuard.validate_and_guard(raw, bad_polished)
    assert is_safe is False
    assert any("Prepended '$'" in w for w in warnings)
    assert final_text == raw
    print("[PASS] Prepending currency symbol to non-currency unit caught and guarded.")


def test_cli_flags_preservation_guard():
    print("\n" + "=" * 65)
    print("TEST: CLI FLAGS PRESERVATION GUARD")
    print("=" * 65)

    raw = "git commit -m initial --dry-run"
    bad_polished = "Git commit initial."  # Dropped -m and --dry-run

    final_text, is_safe, warnings = FactGuard.validate_and_guard(raw, bad_polished)
    assert is_safe is False
    assert any("CLI flag" in w for w in warnings)
    assert final_text == raw
    print("[PASS] Dropped CLI flags rejected and restored.")


def test_soundalike_number_guard():
    print("\n" + "=" * 65)
    print("TEST: SOUNDALIKE NUMBER CONFUSION GUARD (15 vs 50)")
    print("=" * 65)

    raw = "There are fifteen engineers in the meeting"
    bad_polished = "There are 50 engineers in the meeting."

    final_text, is_safe, warnings = FactGuard.validate_and_guard(raw, bad_polished)
    assert is_safe is False
    assert any("Spoken number confusion" in w for w in warnings)
    assert final_text == raw
    print("[PASS] Soundalike number confusion (fifteen -> 50) rejected and restored.")


def test_file_path_preservation_guard():
    print("\n" + "=" * 65)
    print("TEST: FILE PATH PRESERVATION GUARD")
    print("=" * 65)

    raw = "Please inspect config_prod.json before merging"
    bad_polished = "Please inspect config before merging."

    final_text, is_safe, warnings = FactGuard.validate_and_guard(raw, bad_polished)
    assert is_safe is False
    assert final_text == raw
    print("[PASS] Altered file path rejected and restored.")


def test_user_dictionary_preservation_guard():
    print("\n" + "=" * 65)
    print("TEST: USER DICTIONARY TERM PRESERVATION GUARD")
    print("=" * 65)

    raw = "Deploy FlowPilot to the cluster"
    bad_polished = "Deploy the application to the cluster."

    final_text, is_safe, warnings = FactGuard.validate_and_guard(raw, bad_polished, custom_terms=["FlowPilot"])
    assert is_safe is False
    assert any("User dictionary term 'FlowPilot' was dropped" in w for w in warnings)
    assert final_text == raw
    print("[PASS] Dropped user dictionary term rejected and restored.")


def test_transformation_classes():
    print("\n" + "=" * 65)
    print("TEST: TRANSFORMATION CLASSES TAXONOMY")
    print("=" * 65)

    assert TransformationClass.SAFE_FORMATTING == "SAFE_FORMATTING"
    assert TransformationClass.REVIEWABLE_REWRITE == "REVIEWABLE_REWRITE"
    assert TransformationClass.PROTECTED == "PROTECTED"
    print("[PASS] Transformation classes taxonomy verified.")


if __name__ == "__main__":
    test_structured_entity_extraction()
    test_unit_currency_corruption_guard()
    test_cli_flags_preservation_guard()
    test_soundalike_number_guard()
    test_file_path_preservation_guard()
    test_user_dictionary_preservation_guard()
    test_transformation_classes()
    print("\n=======================================================")
    print("ALL FACTGUARD V2 TESTS PASSED (7/7)")
    print("=======================================================")
