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

    print("\n[RESULT] LanguageRegistry tests PASSED.")
    return True

if __name__ == "__main__":
    success = test_language_registry()
    sys.exit(0 if success else 1)
