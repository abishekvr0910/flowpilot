"""
FlowPilot Multilingual Evaluation Metrics — Cross-Language Regression Suite
=======================================================================
Guards the three metric defects that were found while producing the de/es/fr
real-voice baseline (2026-10-22). Each defect would have produced a FALSE PASS
on the critical-entity gate for exactly the languages under test:

1. ``NEGATION_DICTIONARY`` had no de/es/fr entries, so German and French
   negations were never extracted and a dropped ``nicht`` or ``pas`` was
   invisible to the gate.
2. Spanish inverted marks and curly quotes were not stripped from tokens, so a
   sentence starting ``¡Nunca!`` tokenized as ``¡nunca`` and the negation was
   missed.
3. A number spelled out in the reference and rendered as a digit by the
   recognizer counted as a dropped number *plus* a hallucinated one.

Run: ``python -X utf8 tests/test_evaluation_metrics_crosslang.py``
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.evaluation_metrics import (
    extract_critical_entities,
    tokenize_multilingual,
    verify_critical_facts,
)


def test_evaluation_metrics_crosslang():
    print("=" * 72)
    print("   FLOWPILOT EVALUATION METRICS — CROSS-LANGUAGE REGRESSION SUITE")
    print("=" * 72)
    failures = []

    # ---------------------------------------------------------------- 1
    print("\n[1] Negation extraction for de / es / fr")
    print("-" * 72)
    negation_cases = [
        ("de", "Wir haben den Zug nicht verpasst.", "nicht"),
        ("de", "Es gibt keine Ausnahme.", "keine"),
        ("es", "No compramos tres entradas.", "no"),
        ("es", "Sin embargo, la reunión continúa.", "sin"),
        ("fr", "Nous n'avons pas acheté trois billets.", "pas"),
        ("fr", "Il ne reste rien à faire.", "ne"),
    ]
    for language, sentence, expected in negation_cases:
        found = extract_critical_entities(sentence, language=language)["negations"]
        ok = expected in found
        print(f"  {'PASS' if ok else 'FAIL'}  {language}: '{expected}' in {found}")
        if not ok:
            failures.append(f"negation '{expected}' not extracted from {language} sentence")

    # A locale code must resolve to the same table.
    for language, sentence, expected in (("de-DE", "Das ist nicht korrekt.", "nicht"),
                                         ("fr-FR", "Ce n'est pas vrai.", "pas"),
                                         ("es-ES", "Eso no es cierto.", "no")):
        found = extract_critical_entities(sentence, language=language)["negations"]
        ok = expected in found
        print(f"  {'PASS' if ok else 'FAIL'}  locale '{language}': '{expected}' in {found}")
        if not ok:
            failures.append(f"locale '{language}' did not resolve negation '{expected}'")

    # ---------------------------------------------------------------- 2
    print("\n[2] Typographic punctuation is stripped from token edges")
    print("-" * 72)
    token_cases = [
        ("es", "¡Nunca!", "nunca"),
        ("es", "¿Es cierto?", "es"),
        ("de", "„Das stimmt“", "das"),
        ("fr", "«Bonjour»", "bonjour"),
    ]
    for language, raw, expected in token_cases:
        tokens = tokenize_multilingual(raw, language=language)
        ok = expected in tokens
        print(f"  {'PASS' if ok else 'FAIL'}  {language}: {tokens}")
        if not ok:
            failures.append(f"token '{expected}' missing from {raw!r} -> {tokens}")

    # ---------------------------------------------------------------- 3
    print("\n[3] Spelled-out numbers normalise to digits")
    print("-" * 72)
    number_cases = [
        ("es", "Veintidós son los pisos.", "22"),
        ("de", "Zwölf Leute kamen.", "12"),
        ("fr", "Quatre enfants jouent.", "4"),
        ("en", "Twenty people came.", "20"),
    ]
    for language, sentence, expected in number_cases:
        found = extract_critical_entities(sentence, language=language)["numbers"]
        ok = expected in found
        print(f"  {'PASS' if ok else 'FAIL'}  {language}: '{expected}' in {found}")
        if not ok:
            failures.append(f"number '{expected}' not normalised from {sentence!r}")

    # A spelled reference and a digit hypothesis must now compare equal.
    facts = verify_critical_facts(
        "Veintidós son los pisos.", "22 son los pisos.", language="es"
    )
    ok = facts["preserved"] and facts["accuracy"] == 1.0
    print(f"  {'PASS' if ok else 'FAIL'}  spelled reference vs digit hypothesis: "
          f"preserved={facts['preserved']} accuracy={facts['accuracy']}")
    if not ok:
        failures.append("spelled number vs digit hypothesis still compares unequal")

    # ---------------------------------------------------------------- 4
    print("\n[4] A dropped negation is still detected (the gate must fail)")
    print("-" * 72)
    facts = verify_critical_facts(
        "Wir haben den Zug nicht verpasst.", "Wir haben den Zug verpasst.", language="de"
    )
    ok = (not facts["preserved"]) and facts["accuracy"] < 1.0
    print(f"  {'PASS' if ok else 'FAIL'}  dropped 'nicht' detected: "
          f"preserved={facts['preserved']} accuracy={facts['accuracy']} "
          f"missing={facts['missing_negations']}")
    if not ok:
        failures.append("a dropped German negation is not detected by the gate")

    facts = verify_critical_facts(
        "Nous n'avons pas acheté trois billets.", "Nous avons acheté trois billets.", language="fr"
    )
    ok = (not facts["preserved"]) and facts["accuracy"] < 1.0
    print(f"  {'PASS' if ok else 'FAIL'}  dropped 'pas' detected: "
          f"preserved={facts['preserved']} accuracy={facts['accuracy']} "
          f"missing={facts['missing_negations']}")
    if not ok:
        failures.append("a dropped French negation is not detected by the gate")

    # ---------------------------------------------------------------- 5
    print("\n[5] Corpus validator accepts the extended language set")
    print("-" * 72)
    from engine.real_voice_corpus import RealVoiceCorpus
    valid, errors = RealVoiceCorpus().validate_integrity()
    print(f"  {'PASS' if valid else 'FAIL'}  empty corpus valid={valid} errors={errors}")
    if not valid:
        failures.append(f"empty corpus rejected: {errors}")

    for language in ("de", "es", "fr"):
        from engine.real_voice_corpus import CorpusItem
        corpus = RealVoiceCorpus([CorpusItem(
            item_id=f"{language}-probe", language=language, group="clean",
            spoken_reference="Ein kurzer Satz.", formatted_reference="Ein kurzer Satz.",
            speaker_id="probe", consent_verified=True)])
        ok, errs = corpus.validate_integrity()
        print(f"  {'PASS' if ok else 'FAIL'}  language '{language}' accepted by validator")
        if not ok:
            failures.append(f"validator rejected language '{language}': {errs}")

    # ---------------------------------------------------------------- summary
    print("\n" + "=" * 72)
    if failures:
        print(f"RESULT: FAILURES DETECTED ({len(failures)})")
        for failure in failures:
            print(f"  - {failure}")
        print("=" * 72)
        return False
    print("RESULT: ALL CROSS-LANGUAGE METRIC CHECKS PASSED")
    print("=" * 72)
    return True


if __name__ == "__main__":
    sys.exit(0 if test_evaluation_metrics_crosslang() else 1)
