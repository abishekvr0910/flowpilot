import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.language_registry import LanguageRegistry

def test_language_registry():
    print("=" * 60)
    print("TEST: MULTILINGUAL LANGUAGE REGISTRY & DIALECT RULES")
    print("=" * 60)

    # 1. Test listing supported languages
    languages = LanguageRegistry.list_supported_languages()
    print(f"Total supported languages registered: {len(languages)}")
    assert len(languages) >= 15, "Expected at least 15 languages registered"

    # 2. Check key languages and RTL/LTR direction
    en = LanguageRegistry.get_language("en")
    ar = LanguageRegistry.get_language("ar")
    de = LanguageRegistry.get_language("de")
    es = LanguageRegistry.get_language("es")
    fr = LanguageRegistry.get_language("fr")

    assert en is not None and en.direction == "ltr"
    assert ar is not None and ar.direction == "rtl"
    assert de is not None and de.script == "Latin"
    print("Language metadata verified (en, ar, de, es, fr).")

    # 3. Test bias prompt generation
    bias_en = LanguageRegistry.get_bias_prompt("en", ["Kubernetes", "PostgreSQL"])
    print(f"Generated bias prompt (en): '{bias_en}'")
    assert "Kubernetes" in bias_en and "PostgreSQL" in bias_en

    # 4. Test dialect rules: British English
    us_text = "The color of the center theater is organized."
    uk_text = LanguageRegistry.apply_dialect_rules(us_text, "en-GB")
    print(f"British English transformation:\n  Original: '{us_text}'\n  UK:       '{uk_text}'")
    assert "colour" in uk_text and "centre" in uk_text and "theatre" in uk_text and "organised" in uk_text

    # 5. Test dialect rules: Swiss German (no ß)
    de_text = "Bitte die Straße und das Maßband prüfen."
    ch_text = LanguageRegistry.apply_dialect_rules(de_text, "de-CH")
    print(f"Swiss German transformation:\n  Original: '{de_text}'\n  Swiss:    '{ch_text}'")
    assert "Strasse" in ch_text and "Massband" in ch_text

    # 6. Test dialect rules: French spacing before punctuation
    fr_text = "Comment allez-vous? Très bien!"
    fr_spaced = LanguageRegistry.apply_dialect_rules(fr_text, "fr")
    print(f"French punctuation spacing:\n  Original: '{fr_text}'\n  Spaced:   '{fr_spaced}'")
    assert " ?" in fr_spaced and " !" in fr_spaced

    # 7. Test Tamil ('ta') and Malayalam ('ml') registration, native names, and experimental status
    ta = LanguageRegistry.get_language("ta")
    ml = LanguageRegistry.get_language("ml")

    assert ta is not None, "Tamil (ta) must be registered in LanguageRegistry"
    assert ta.name == "Tamil"
    assert ta.native_name == "தமிழ்"
    assert ta.script == "Tamil"
    assert ta.direction == "ltr"
    assert ta.quality_status == "experimental"
    assert ta.recommended_model == "small"
    assert "\u200b" not in ta.native_name, "Accidental zero-width spaces must not be in Tamil label"

    assert ml is not None, "Malayalam (ml) must be registered in LanguageRegistry"
    assert ml.name == "Malayalam"
    assert ml.native_name == "മലയാളം"
    assert ml.script == "Malayalam"
    assert ml.direction == "ltr"
    assert ml.quality_status == "experimental"
    assert ml.recommended_model == "small"
    assert "\u200b" not in ml.native_name, "Accidental zero-width spaces must not be in Malayalam label"

    # 8. Test serialization and picker listing
    ta_dict = ta.to_dict()
    assert ta_dict["code"] == "ta"
    assert ta_dict["quality_status"] == "experimental"

    ml_dict = ml.to_dict()
    assert ml_dict["code"] == "ml"
    assert ml_dict["quality_status"] == "experimental"

    # Verify list_supported_languages propagates quality_status and includes ta/ml
    supported = LanguageRegistry.list_supported_languages()
    codes = [item["code"] for item in supported]
    assert "ta" in codes and "ml" in codes
    assert codes[0] == "auto", "Auto must be the first language entry"
    assert codes.count("auto") == 1, "Auto must not appear multiple times in list"

    # 9. Test native bias prompt generation for ta and ml
    bias_ta = LanguageRegistry.get_bias_prompt("ta", ["React", "FastAPI"])
    assert "தமிழ்" in bias_ta or len(bias_ta) > 0
    assert "React" in bias_ta and "FastAPI" in bias_ta

    bias_ml = LanguageRegistry.get_bias_prompt("ml", ["Docker", "Kubernetes"])
    assert "മലയാളം" in bias_ml or len(bias_ml) > 0
    assert "Docker" in bias_ml and "Kubernetes" in bias_ml

    print("\n[RESULT] LanguageRegistry tests PASSED.")

if __name__ == "__main__":
    test_language_registry()
    sys.exit(0)
