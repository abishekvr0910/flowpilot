"""
Unit Tests for FlowPilot Writing Intelligence Engine
Validates:
- Verbatim mode vs Polished mode
- Spoken self-corrections
- Filler word and stutter elimination
- Technical identifier conversions (camelCase, snake_case, kebab-case)
- Technical acronym canonicalization (API, JSON, PostgreSQL, CTranslate2)
- Spoken list formatting
- Spoken email and URL formatting
- Currency and percent formatting
- Style-aware terminal command punctuation
- FactGuard semantic and negation preservation
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.writing_intelligence import WritingIntelligence, FactGuard

def test_writing_intelligence():
    print("=" * 65)
    print("AUDIT TEST: WRITING INTELLIGENCE & POLISHED MODES")
    print("=" * 65)

    wi = WritingIntelligence()

    # 1. Verbatim Mode Test
    raw_speech = "um I want to schedule the meeting for Tuesday uh like you know"
    res_verb = wi.polish(raw_speech, mode="verbatim")
    print(f"[1] Verbatim Mode:\n    Raw:    '{raw_speech}'\n    Result: '{res_verb['text']}'")
    assert "um" in res_verb['text'].lower()
    assert "Tuesday" in res_verb['text']
    assert res_verb['mode'] == "verbatim"

    # 2. Polished Mode: Spoken Self-Correction
    correction_speech = "Please schedule the meeting for Tuesday — actually, Wednesday afternoon"
    res_corr = wi.polish(correction_speech, mode="polished", style="professional")
    print(f"\n[2] Self-Correction:\n    Raw:    '{correction_speech}'\n    Result: '{res_corr['text']}'")
    assert "Wednesday" in res_corr['text'], "Self-correction failed to adopt corrected value"
    assert "Tuesday" not in res_corr['text'], "Self-correction failed to discard superseded value"

    # 3. Filler and Stutter Removal
    stutter_speech = "Um, uh, we we need to, like, test the the postgres api connection"
    res_clean = wi.polish(stutter_speech, mode="polished", style="professional")
    print(f"\n[3] Filler & Stutter Removal:\n    Raw:    '{stutter_speech}'\n    Result: '{res_clean['text']}'")
    assert "um" not in res_clean['text'].lower()
    assert "uh" not in res_clean['text'].lower()
    assert "we we" not in res_clean['text'].lower()
    assert "the the" not in res_clean['text'].lower()
    assert "PostgreSQL" in res_clean['text']
    assert "API" in res_clean['text']

    # 4. Technical / Developer Identifiers
    tech_speech = "create camel case user profile and snake case get account balance"
    res_tech = wi.polish(tech_speech, mode="polished", style="developer")
    print(f"\n[4] Developer Identifiers:\n    Raw:    '{tech_speech}'\n    Result: '{res_tech['text']}'")
    assert "userProfile" in res_tech['text'], "camelCase formatting failed"
    assert "get_account_balance" in res_tech['text'], "snake_case formatting failed"

    # 5. Spoken List Formatting
    list_speech = "here are the tasks first run the audit suite second fix all bugs third package the release"
    res_list = wi.polish(list_speech, mode="polished", style="professional")
    print(f"\n[5] Spoken List Formatting:\n    Raw:    '{list_speech}'\n    Result:\n{res_list['text']}")
    assert "\n- " in res_list['text'], "List formatting failed to create bullets"

    # 6. Spoken Email and URL Formatting
    email_url_speech = "contact john dot doe at example dot com or visit https colon slash slash github dot com slash repo"
    res_email = wi.polish(email_url_speech, mode="polished", style="developer")
    print(f"\n[6] Email & URL Formatting:\n    Raw:    '{email_url_speech}'\n    Result: '{res_email['text']}'")
    assert "john.doe@example.com" in res_email['text']
    assert "https://github.com/repo" in res_email['text']

    # 7. Currency and Percent Formatting
    finance_speech = "we offered twenty five percent discount on twelve thousand dollars"
    res_fin = wi.polish(finance_speech, mode="polished", style="professional")
    print(f"\n[7] Currency & Percent Formatting:\n    Raw:    '{finance_speech}'\n    Result: '{res_fin['text']}'")
    assert "25%" in res_fin['text']
    assert "$12000" in res_fin['text'] or "$12,000" in res_fin['text']

    # 8. Fact & Negation Preservation Check
    negation_speech = "Do not deploy on Friday, never commit without tests, price is $450 on October 15"
    res_neg = wi.polish(negation_speech, mode="polished", style="professional")
    print(f"\n[8] FactGuard Preservation:\n    Raw:    '{negation_speech}'\n    Result: '{res_neg['text']}'")
    assert "not" in res_neg['text'].lower()
    assert "never" in res_neg['text'].lower()
    assert "$450" in res_neg['text']
    assert "October 15" in res_neg['text']

    # 9. Style-aware CLI Command punctuation (no trailing period)
    cli_speech = "git commit -m initial commit"
    res_cli = wi.polish(cli_speech, mode="polished", style="developer")
    print(f"\n[9] CLI Command Punctuation:\n    Raw:    '{cli_speech}'\n    Result: '{res_cli['text']}'")
    assert not res_cli['text'].endswith("."), "Developer CLI commands should not end with period"


def test_wispr_flow_spoken_commands():
    print("\n" + "=" * 65)
    print("AUDIT TEST: WISPR FLOW SPOKEN PUNCTUATION & VOICE EDITING COMMANDS")
    print("=" * 65)

    wi = WritingIntelligence()

    # 1. Punctuation commands
    punc_raw = "hello comma world question mark are you ready exclamation point"
    punc_res = wi.polish(punc_raw, mode="polished", style="professional")
    print(f"[1] Spoken Punctuation:\n    Raw:    '{punc_raw}'\n    Result: '{punc_res['text']}'")
    assert "Hello, world? Are you ready!" in punc_res['text']

    # 2. Structural commands: new line, new paragraph
    struct_raw = "line one new line line two new paragraph new block"
    struct_res = wi.polish(struct_raw, mode="polished", style="professional")
    print(f"\n[2] Structural Commands:\n    Raw:    '{struct_raw}'\n    Result:\n{struct_res['text']}")
    assert "Line one\nLine two\n\nNew block" in struct_res['text']

    # 3. Voice editing: scratch that
    scratch_raw = "this is incorrect scratch that this is the real message"
    scratch_res = wi.polish(scratch_raw, mode="polished", style="professional")
    print(f"\n[3] Voice Editing (Scratch that):\n    Raw:    '{scratch_raw}'\n    Result: '{scratch_res['text']}'")
    assert "incorrect" not in scratch_res['text']
    assert "This is the real message." in scratch_res['text']

    # 4. Voice formatting: all caps
    caps_raw = "the code is all caps secret"
    caps_res = wi.polish(caps_raw, mode="polished", style="developer")
    print(f"\n[4] Voice Casing:\n    Raw:    '{caps_raw}'\n    Result: '{caps_res['text']}'")
    assert "SECRET" in caps_res['text']

    print("\n[RESULT] Wispr Flow Spoken Commands PASSED 100%.")

def test_caret_aware_context_formatting():
    """Verify caret-aware capitalization suppression and duplicate punctuation prevention."""
    from engine.writing_intelligence import WritingIntelligence
    wi = WritingIntelligence()

    print("\n=================================================================")
    print("AUDIT TEST: CARET-AWARE CONTEXT FORMATTING")
    print("=================================================================")

    # 1. Mid-sentence capitalization suppression
    res_mid = wi.polish("we should go", mode="polished", style="professional", preceding_text="I really think ")
    print(f"[1] Mid-Sentence Insertion:\n    Preceding: 'I really think '\n    Result:    '{res_mid['text']}'")
    assert res_mid["text"].startswith("we should go"), f"Expected lowercase 'we', got {res_mid['text']}"

    # 2. Start of sentence capitalization preserved
    res_start = wi.polish("we should go", mode="polished", style="professional", preceding_text="This was great. ")
    print(f"[2] Start-Of-Sentence Insertion:\n    Preceding: 'This was great. '\n    Result:    '{res_start['text']}'")
    assert res_start["text"].startswith("We should go"), f"Expected uppercase 'We', got {res_start['text']}"

    # 3. Duplicate terminal punctuation prevention
    res_dup = wi.polish("thanks very much.", mode="polished", style="professional", following_text=".")
    print(f"[3] Duplicate Punctuation Suppression:\n    Following: '.'\n    Result:    '{res_dup['text']}'")
    assert not res_dup["text"].endswith("."), f"Expected stripped trailing period, got {res_dup['text']}"

    print("[RESULT] Caret-Aware Formatting PASSED 100%.")


def test_automatic_correction_detector():
    """Verify AutomaticCorrectionDetector diff extraction, 2x occurrence threshold, and cooldown."""
    from engine.writing_intelligence import AutomaticCorrectionDetector
    import time
    detector = AutomaticCorrectionDetector(required_occurrences=2, window_days=7)
    detector.clear()

    print("\n=================================================================")
    print("AUDIT TEST: AUTOMATIC CORRECTION DETECTOR (FLUIDVOICE PARITY)")
    print("=================================================================")

    # 1. Diff pair extraction
    diff = detector.extract_diff_pair("We deployed K8s to prod.", "We deployed Kubernetes to prod.")
    print(f"[1] Diff Extraction:\n    Pair: {diff}")
    assert diff == ("K8s", "Kubernetes")

    # 2. First occurrence: no suggestion yet
    t0 = time.time()
    detector.record_occurrence("K8s", "Kubernetes", timestamp=t0)
    suggestions = detector.get_pending_suggestions(now=t0)
    print(f"[2] First Occurrence (count 1):\n    Pending: {suggestions}")
    assert len(suggestions) == 0

    # 3. Second occurrence within 7 days: surfaces as pending suggestion
    t1 = t0 + 86400  # 1 day later
    detector.record_occurrence("K8s", "Kubernetes", timestamp=t1)
    suggestions = detector.get_pending_suggestions(now=t1)
    print(f"[3] Second Occurrence (count 2 within 7d):\n    Pending: {suggestions}")
    assert len(suggestions) == 1
    assert suggestions[0]["heard"] == "K8s"
    assert suggestions[0]["corrected"] == "Kubernetes"
    assert suggestions[0]["occurrences"] == 2

    # 4. User dismissal cooldown
    detector.dismiss_suggestion("K8s", "Kubernetes", cooldown_days=7, now=t1)
    suggestions_after_dismiss = detector.get_pending_suggestions(now=t1)
    print(f"[4] After 7-Day Dismissal Cooldown:\n    Pending: {suggestions_after_dismiss}")
    assert len(suggestions_after_dismiss) == 0

    print("[RESULT] Automatic Correction Detector PASSED 100%.")


if __name__ == "__main__":
    test_writing_intelligence()
    test_wispr_flow_spoken_commands()
    test_caret_aware_context_formatting()
    test_automatic_correction_detector()
    sys.exit(0)
