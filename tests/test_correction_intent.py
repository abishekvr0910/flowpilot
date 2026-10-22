"""
FlowPilot Correction Intent Engine — Regression Suite
=====================================================
Locks in the behaviour of ``engine.correction_intent.CorrectionIntentResolver``.

The suite is split into three groups:

A. RESOLUTION — spoken corrections must be resolved correctly.
B. MEANING PRESERVATION — a marker word used as an intensifier must never
   trigger a rewrite. These are the regressions that motivated the engine:
   the previous implementation turned "I actually enjoyed the movie" into
   "Enjoyed the movie."
C. FACTGUARD INTEGRITY — a trigger phrase that contains a protected token
   ("no" in "no wait", "never" in "never mind") must not cause FactGuard to
   silently revert the whole correction.

Run: ``python -X utf8 tests/test_correction_intent.py``
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.writing_intelligence import WritingIntelligence
from engine.correction_intent import CorrectionIntentResolver


def _norm(text):
    """Normalise for comparison: case, trailing punctuation, extra spaces."""
    return " ".join(text.lower().strip().rstrip(".!?").split())


def test_correction_intent():
    print("=" * 72)
    print("       FLOWPILOT CORRECTION INTENT ENGINE — REGRESSION SUITE")
    print("=" * 72)

    resolver = CorrectionIntentResolver(language="en")
    wi = WritingIntelligence()
    failures = []

    # ---------------------------------------------------------------- A
    print("\n[A] RESOLUTION — spoken corrections are resolved")
    print("-" * 72)

    resolution_cases = [
        (
            "A-01 temporal value",
            "schedule it for Tuesday actually Wednesday",
            "schedule it for wednesday",
        ),
        (
            "A-02 numeric value",
            "the budget is 5000 actually 6000 dollars",
            "the budget is 6000 dollars",
        ),
        (
            "A-03 numeric with unit",
            "let us meet at 2 actually 3 pm",
            "let us meet at 3 pm",
        ),
        (
            "A-04 proper noun via 'sorry'",
            "send this to John sorry Jane",
            "send this to jane",
        ),
        (
            "A-05 quantity phrase via bare 'wait'",
            "we have five wait six members",
            "we have six members",
        ),
        (
            "A-06 retraction marker 'never mind'",
            "meet at 2 never mind 3",
            "meet at 3",
        ),
        (
            "A-07 'no wait' with repeated verb",
            "call John no wait call Jane",
            "call jane",
        ),
        (
            "A-08 quantity phrase via 'no wait'",
            "send 5 copies no wait 10 copies",
            "send 10 copies",
        ),
        (
            "A-09 multiple corrections in one utterance",
            "bring 5 laptops actually 3 laptops and also 2 monitors actually 4 monitors",
            "bring 3 laptops and also 4 monitors",
        ),
        (
            "A-10 'i mean' marker",
            "the meeting is Thursday I mean Friday",
            "the meeting is friday",
        ),
        (
            "A-11 'or rather' marker",
            "meet at 2:00 or rather 3:00",
            "meet at 3:00",
        ),
        (
            "A-12 negation retraction",
            "Please do not proceed -- actually, proceed immediately",
            "please do proceed immediately",
        ),
    ]

    for name, raw, expected in resolution_cases:
        resolved, _nums, _negs, applied = resolver.resolve(raw)
        ok = _norm(resolved) == _norm(expected)
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        print(f"        raw       : {raw}")
        print(f"        resolved  : {resolved}")
        if not ok:
            print(f"        expected  : {expected}")
            failures.append(f"{name}: got '{resolved}', expected '{expected}'")
        if not applied:
            failures.append(f"{name}: no correction was applied")
            print(f"        !! no correction applied")

    # ---------------------------------------------------------------- B
    print("\n[B] MEANING PRESERVATION — intensifiers must not rewrite text")
    print("-" * 72)

    preservation_cases = [
        ("B-01 'actually' as intensifier", "I actually enjoyed the movie"),
        ("B-02 'actually' with auxiliary", "we were actually going to leave early"),
        ("B-03 'actually' before a verb", "the coffee actually tastes great"),
        ("B-04 ordinary 'wait' verb", "please wait for the server to respond"),
        ("B-05 'sorry' as an apology", "sorry about the earlier delay"),
        ("B-06 'actually' in a non-correction clause", "the meeting was actually useful"),
        ("B-07 'never' as a real negation", "we will never deploy on Friday"),
    ]

    for name, raw in preservation_cases:
        resolved, _nums, _negs, applied = resolver.resolve(raw)
        ok = _norm(resolved) == _norm(raw)
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        print(f"        raw       : {raw}")
        print(f"        resolved  : {resolved}")
        if not ok:
            failures.append(f"{name}: '{raw}' was rewritten to '{resolved}'")
        if applied:
            failures.append(f"{name}: a correction was applied where none was intended")

    # ---------------------------------------------------------------- C
    print("\n[C] FACTGUARD INTEGRITY — triggers must survive the semantic guard")
    print("-" * 72)

    guard_cases = [
        (
            "C-01 'no wait' (trigger contains the negation 'no')",
            "call John no wait call Jane",
            ["Jane"],
            ["John"],
        ),
        (
            "C-02 'never mind' (trigger contains the negation 'never')",
            "meet at 2 never mind 3",
            ["3"],
            ["2"],
        ),
        (
            "C-03 'sorry' name correction",
            "send this to John sorry Jane",
            ["Jane"],
            ["John"],
        ),
    ]

    for name, raw, must_contain, must_not_contain in guard_cases:
        result = wi.polish(raw, style="professional")
        polished = result["text"]
        ok = all(token.lower() in polished.lower() for token in must_contain) and all(
            token.lower() not in polished.lower() for token in must_not_contain
        )
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        print(f"        raw       : {raw}")
        print(f"        polished  : {polished}")
        if not ok:
            failures.append(f"{name}: polished '{polished}' failed the expected content")

    # The end-to-end polish path must keep the corrected value, not the raw one.
    print("\n  [C-04] End-to-end polish keeps the corrected value")
    e2e = wi.polish("the budget is 5000 actually 6000 dollars", style="professional")
    digits = e2e["text"].replace(",", "")
    e2e_ok = "6000" in digits and "5000" not in digits
    print(f"  {'PASS' if e2e_ok else 'FAIL'}  polished: {e2e['text']}")
    if not e2e_ok:
        failures.append(f"C-04: polished '{e2e['text']}' lost the corrected value")

    # ---------------------------------------------------------------- summary
    print("\n" + "=" * 72)
    if failures:
        print(f"RESULT: FAILURES DETECTED ({len(failures)})")
        for failure in failures:
            print(f"  - {failure}")
        print("=" * 72)
        return False

    total = len(resolution_cases) + len(preservation_cases) + len(guard_cases) + 1
    print(f"RESULT: ALL {total} CORRECTION INTENT CHECKS PASSED")
    print("=" * 72)
    return True


if __name__ == "__main__":
    sys.exit(0 if test_correction_intent() else 1)
