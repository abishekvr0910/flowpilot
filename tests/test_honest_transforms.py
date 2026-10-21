"""
Tests for FlowPilot Honest Transforms, Result Contract & Apply Guardrails (Track C)
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.transforms_engine import TransformsEngine, TransformResult

def test_no_llm_replace_friday_with_monday_unsupported():
    """Without an LLM, 'replace Friday with Monday' returns unsupported, exact text unchanged, Apply blocked."""
    engine = TransformsEngine()
    original = "Let's meet on Friday at 3pm to review the deployment."

    # Ensure local LLM is reported unavailable
    mock_llm = MagicMock()
    mock_llm.is_available.return_value = False

    with patch("engine.local_llm.get_local_llm", return_value=mock_llm):
        with patch("engine.text_injector.TextInjector.inject_with_status") as mock_inject:
            res = engine.transform_text(original, "custom", custom_instruction="replace Friday with Monday")

            # 1. Honest status
            assert res.status == "unsupported"
            assert res.execution_route == "none"
            assert res.guard_status == "not_run"
            assert res.can_apply is False
            assert res.reason_code == "LOCAL_LLM_REQUIRED"
            assert "needs the optional local writing model" in res.error_message

            # 2. Exact unchanged text preserved
            assert res.candidate_text == original
            assert res.original_text == original

            # 3. Apply blocked
            applied = engine.replace_selection(res.candidate_text, result=res)
            assert applied is False
            assert mock_inject.call_count == 0

def test_preserves_whitespace_blank_lines_and_non_latin():
    """Unsuccessful transform preserves leading/trailing whitespace, blank lines and non-Latin text."""
    engine = TransformsEngine()
    original = "   \n\n  வணக்கம் உலகம்! Здравствуйте мир!   \n  "

    mock_llm = MagicMock()
    mock_llm.is_available.return_value = False

    with patch("engine.local_llm.get_local_llm", return_value=mock_llm):
        res = engine.transform_text(original, "custom", custom_instruction="rephrase this passage")
        assert res.status == "unsupported"
        assert res.candidate_text == original
        assert res.can_apply is False

def test_unrelated_keywords_do_not_trigger_false_presets():
    """Keywords 'pro', 'list', 'work', 'short' do not trigger unintended presets or compound partial execution."""
    engine = TransformsEngine()
    mock_llm = MagicMock()
    mock_llm.is_available.return_value = False

    with patch("engine.local_llm.get_local_llm", return_value=mock_llm):
        # 'pro' in 'production'
        res1 = engine.transform_text("Deploy to production", "custom", custom_instruction="replace production with staging")
        assert res1.status == "unsupported", "Must not trigger professional tone on 'production'"

        # 'list' in 'checklist'
        res2 = engine.transform_text("Item one", "custom", custom_instruction="verify this checklist item")
        assert res2.status == "unsupported", "Must not trigger bullet points on 'checklist'"

        # Compound instruction
        res3 = engine.transform_text("Sentence one. Sentence two.", "custom", custom_instruction="make concise and fix grammar")
        assert res3.status == "unsupported", "Compound instruction must not partially execute without LLM"

def test_approved_deterministic_aliases_still_work():
    """Anchored approved aliases ('make concise', 'bullet list') work deterministically without LLM."""
    engine = TransformsEngine()
    mock_llm = MagicMock()
    mock_llm.is_available.return_value = False

    with patch("engine.local_llm.get_local_llm", return_value=mock_llm):
        # Approved bullet points alias
        res_b = engine.transform_text("Alpha; Beta; Gamma", "custom", custom_instruction="format as bullet points")
        assert res_b.status == "success"
        assert res_b.execution_route == "deterministic"
        assert res_b.can_apply is True
        assert "- Alpha" in res_b.candidate_text

        # Approved concise alias
        res_c = engine.transform_text("At the end of the day, we basically need to finish this.", "custom", custom_instruction="make concise")
        assert res_c.status == "success"
        assert res_c.execution_route == "deterministic"
        assert res_c.can_apply is True
        assert "basically" not in res_c.candidate_text.lower()

def test_translation_unavailable_without_llm():
    """Text translation returns unavailable and preserves original text when local LLM is absent."""
    engine = TransformsEngine()
    mock_llm = MagicMock()
    mock_llm.is_available.return_value = False

    original = "Bonjour tout le monde. Ceci est un test important."
    with patch("engine.local_llm.get_local_llm", return_value=mock_llm):
        res = engine.transform_text(original, "translate_en")
        assert res.status == "unavailable"
        assert res.can_apply is False
        assert res.reason_code == "TRANSLATION_MODEL_UNAVAILABLE"
        assert res.candidate_text == original, "Translation must not silently shorten text when model is unavailable"

def test_factguard_violation_is_blocked_not_mislabeled():
    """A transform that alters numbers or dates is blocked by FactGuard, distinct from unsupported."""
    engine = TransformsEngine()

    # Preset fix_grammar on text
    original = "We made $500 on Friday."
    # If a rule or candidate changes digits to $900
    with patch.object(engine, "_apply_grammar_fix", return_value="We made $900 on Friday."):
        res = engine.transform_text(original, "fix_grammar")
        assert res.status == "blocked"
        assert res.guard_status == "failed"
        assert res.reason_code == "FACTGUARD_INVARIANT_VIOLATION"
        assert res.can_apply is False
        # Blocked in replace_selection
        applied = engine.replace_selection(res.candidate_text, result=res)
        assert applied is False

def test_unsuccessful_request_does_not_destroy_previous_undo():
    """An unsuccessful request must not overwrite the last successful undo transaction."""
    engine = TransformsEngine()
    first_orig = "I basically agree."
    first_res = engine.transform_text(first_orig, "make_concise")
    assert first_res.status == "success"
    assert engine._last_original_text == first_orig
    assert engine._last_can_apply is True

    # Now run an unsupported request
    mock_llm = MagicMock()
    mock_llm.is_available.return_value = False
    with patch("engine.local_llm.get_local_llm", return_value=mock_llm):
        second_res = engine.transform_text("Another text", "custom", custom_instruction="replace Friday with Monday")
        assert second_res.status == "unsupported"
        assert engine._last_can_apply is False
        # Last original text is NOT destroyed
        assert engine._last_original_text == first_orig

def test_tuple_unpacking_fails_closed():
    """Legacy tuple unpacking (transformed, ok) evaluates ok to False on unsupported or blocked."""
    engine = TransformsEngine()
    mock_llm = MagicMock()
    mock_llm.is_available.return_value = False

    with patch("engine.local_llm.get_local_llm", return_value=mock_llm):
        out, ok = engine.transform_text("Friday meeting", "custom", custom_instruction="replace Friday with Monday")
        assert ok is False, "Legacy caller must receive ok=False"
        assert out == "Friday meeting"

if __name__ == "__main__":
    print("Running Honest Transforms tests...")
    test_no_llm_replace_friday_with_monday_unsupported()
    test_preserves_whitespace_blank_lines_and_non_latin()
    test_unrelated_keywords_do_not_trigger_false_presets()
    test_approved_deterministic_aliases_still_work()
    test_translation_unavailable_without_llm()
    test_factguard_violation_is_blocked_not_mislabeled()
    test_unsuccessful_request_does_not_destroy_previous_undo()
    test_tuple_unpacking_fails_closed()
    print("[RESULT] Honest Transforms tests PASSED.")
    sys.exit(0)
