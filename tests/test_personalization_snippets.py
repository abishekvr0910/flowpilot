"""
FlowPilot Voice Snippets Hardening Regression Tests
Verifies:
1. Whole-word regex boundary enforcement (prevent mid-word triggers)
2. Longest-match trigger precedence on overlapping phrases
3. Overlapping trigger conflict detection
4. Literal expansion safety (zero command/regex injection)
"""

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.personalization import PersonalizationEngine

def test_snippet_boundaries_and_precedence():
    print("=" * 65)
    print("TEST: VOICE SNIPPET BOUNDARIES & PRECEDENCE")
    print("=" * 65)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "test_personalization.json"
        engine = PersonalizationEngine(storage_path=tmp_path)
        engine.snippets = []

        # Add shorter and longer triggers
        res1 = engine.add_snippet("insert calendly", "https://calendly.com/short")
        res2 = engine.add_snippet("insert calendly link", "https://calendly.com/longer-specific-url")

        assert res1["status"] == "added"
        assert res2["status"] == "added"
        assert len(res2["warnings"]) > 0  # Warns about overlapping sub-trigger
        print("[PASS] Overlapping trigger warning issued correctly.")

        # 1. Longest match precedence check
        text_long = "Please use insert calendly link to book time."
        expanded_long, trig_long = engine.expand_snippets(text_long)
        assert trig_long == "insert calendly link"
        assert expanded_long == "Please use https://calendly.com/longer-specific-url to book time."
        print("[PASS] Longest match precedence honored over shorter prefix trigger.")

        # 2. Short match check
        text_short = "Please use insert calendly to book."
        expanded_short, trig_short = engine.expand_snippets(text_short)
        assert trig_short == "insert calendly"
        assert expanded_short == "Please use https://calendly.com/short to book."
        print("[PASS] Shorter trigger matched when longer trigger is not present.")

        # 3. Whole-word boundary check (mid-word must NOT expand)
        text_midword = "Do not reinsert calendly today."
        expanded_mid, trig_mid = engine.expand_snippets(text_midword)
        assert trig_mid is None
        assert expanded_mid == text_midword
        print("[PASS] Whole-word boundaries prevent accidental mid-word expansion.")


def test_literal_expansion_safety():
    print("\n" + "=" * 65)
    print("TEST: LITERAL EXPANSION SAFETY (NO REGEX INJECTION)")
    print("=" * 65)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "test_personalization.json"
        engine = PersonalizationEngine(storage_path=tmp_path)
        engine.snippets = []

        # Expansion containing regex backreferences and special characters
        adversarial_expansion = r"Template \1 with $2 and \g<0> literal chars"
        engine.add_snippet("insert test template", adversarial_expansion)

        text = "Please insert test template now."
        expanded, trig = engine.expand_snippets(text)
        assert trig == "insert test template"
        assert adversarial_expansion in expanded
        print("[PASS] Adversarial regex backreferences handled as 100% static literals.")


if __name__ == "__main__":
    test_snippet_boundaries_and_precedence()
    test_literal_expansion_safety()
    print("\n=======================================================")
    print("ALL PERSONALIZATION SNIPPET TESTS PASSED (2/2)")
    print("=======================================================")
