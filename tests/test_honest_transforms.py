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
from engine.text_injector import TextInjector, InjectionResult, InjectionStatus

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
            assert applied.status == InjectionStatus.CANCELLED
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
        assert applied.status == InjectionStatus.CANCELLED

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

def test_guarded_injector_refuses_after_focus_loss_no_unicode_fallback():
    """Unverifiable external operations never reach either input method."""
    engine = TransformsEngine()
    res = engine.transform_text("A basically simple sentence.", "make_concise")
    assert res.can_apply is True

    # Mock inject_with_status returning FAILED_RECOVERY_AVAILABLE (simulated focus switch away from target)
    refusal_result = InjectionResult(
        status=InjectionStatus.FAILED_RECOVERY_AVAILABLE,
        error_message="Active window focus lost to another process."
    )

    tx = MagicMock()
    tx.target_type = "scratchpad"
    tx.consumed = False

    with patch.object(TextInjector, "inject_with_status", return_value=refusal_result) as mock_inject:
        with patch.object(TextInjector, "inject_unicode_sendinput") as mock_sendinput:
            inj_res = engine.replace_selection(res.candidate_text, result=res, transaction=tx)

            assert mock_inject.call_count == 0
            assert mock_sendinput.call_count == 0
            assert inj_res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE
            assert "cannot be verified" in inj_res.error_message.lower()


def test_missing_closed_or_changed_target_refuses_preserves_recovery():
    """Missing or closed target refuses operation and keeps text in memory recovery buffer."""
    engine = TransformsEngine()
    res = engine.transform_text("Deploy to staging.", "fix_grammar")
    assert res.can_apply is True

    tx = MagicMock()
    tx.target_type = "scratchpad"
    tx.consumed = False

    # Simulate closed window HWND 999999
    refusal = InjectionResult(
        status=InjectionStatus.FAILED_RECOVERY_AVAILABLE,
        error_message="Target HWND 999999 is no longer valid. Preserved in recovery buffer.",
        recovery_available=True
    )
    with patch.object(TextInjector, "inject_with_status", return_value=refusal):
        inj_res = engine.replace_selection(res.candidate_text, target_hwnd=999999, result=res, transaction=tx)
        assert inj_res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE
        assert inj_res.recovery_available is True
        assert TextInjector.last_injected_text == res.candidate_text


def test_sent_unverified_retains_outcome_no_confirmed_message():
    """The UI never turns an unverified delivery result into a confirmed edit."""
    from types import SimpleNamespace
    from ui.transforms_view import TransformsView
    unverified = InjectionResult(
        status=InjectionStatus.SENT_UNVERIFIED,
        chars_sent=10,
        target_title="Opaque Editor"
    )
    view = SimpleNamespace(
        engine=MagicMock(), _current_result=SimpleNamespace(can_apply=True),
        edit_transformed=MagicMock(), transform_applied=MagicMock(),
    )
    view.edit_transformed.toPlainText.return_value = "Preview text"
    view.engine.replace_selection.return_value = unverified
    view.engine.revert_last_transform.return_value = unverified
    with patch("ui.transforms_view.QMessageBox") as messages:
        TransformsView._replace_in_target(view)
        TransformsView._revert_last(view)
    view.transform_applied.emit.assert_not_called()
    assert messages.information.call_count == 2
    for call in messages.information.call_args_list:
        assert "please check" in call.args[2].lower()
        assert "restored original" not in call.args[2].lower()


def test_external_mutation_without_verifiable_transaction_refuses():
    """External in-place mutation without verified transaction adapter refuses safely and keeps text in memory."""
    engine = TransformsEngine()
    res = engine.transform_text("We basically finished.", "make_concise")
    assert res.can_apply is True

    # No verified transaction provided (external window)
    inj_res = engine.replace_selection(res.candidate_text, result=res, transaction=None)
    assert inj_res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE
    assert "external in-place replacement unavailable" in inj_res.error_message.lower()
    assert TextInjector.last_injected_text == res.candidate_text


def test_selection_or_document_changed_after_planning_refuses():
    """Exercise actual scratchpad revision and selection guards."""
    from engine.voice_editor import VoiceEditor
    original = "The meeting is on Friday."
    for current_text, current_selection in ((original + " New text.", (6, 6)), (original, (7, 7))):
        editor = VoiceEditor()
        tx = editor.plan_edit(original, (6, 6), "replace Friday with Monday", target_id="scratchpad:test")
        assert tx.can_apply
        ok, resulting_text, message = editor.apply_transaction(
            tx, current_text, current_selection, current_target_id="scratchpad:test",
        )
        assert not ok
        assert resulting_text == current_text
        assert "modified concurrently" in message.lower() or "selection changed" in message.lower()


def test_revert_invoked_twice_refuses_second_call():
    """Repeating an unsupported external revert never reinserts original text."""
    engine = TransformsEngine()
    engine.transform_text("First version.", "make_concise")
    with patch.object(TextInjector, "inject_with_status", side_effect=AssertionError("Unexpected dispatch")), \
         patch.object(TextInjector, "inject_unicode_sendinput", side_effect=AssertionError("Unexpected typing")):
        for _ in range(2):
            outcome = engine.revert_last_transform(target_hwnd=12345)
            assert outcome.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE
            assert TextInjector.last_injected_text == "First version."


def test_clipboard_changed_by_user_during_abort_preserved():
    """User clipboard modifications during an aborted operation remain intact."""
    import pyperclip
    engine = TransformsEngine()
    res = engine.transform_text("Important sentence.", "make_concise")

    user_data = "A newer user copy"
    # Never put test fixtures on the user's real system clipboard.
    with patch.object(pyperclip, "paste", return_value=user_data) as clipboard_read, \
         patch.object(pyperclip, "copy", side_effect=AssertionError("Unexpected clipboard write")):
        inj_res = engine.replace_selection(res.candidate_text, result=res, transaction=None)
        assert inj_res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE
        assert pyperclip.paste() == user_data
        assert clipboard_read.call_count == 1


def test_scratchpad_edit_and_undo_transactions_still_work():
    """Existing scratchpad guarded transactions and undo continue working seamlessly."""
    from engine.voice_editor import VoiceEditor

    editor = VoiceEditor()
    initial_doc = "The meeting is on Friday at three."
    tx = editor.plan_edit(initial_doc, (0, 0), "replace Friday with Monday", target_id="scratchpad:editor")
    assert tx.status == "pending"
    assert tx.can_apply is True
    assert "Monday" in tx.candidate_text

    ok, applied_doc, err = editor.apply_transaction(tx, initial_doc)
    assert ok is True
    assert "Monday" in applied_doc

    # Genuine undo transaction verified against document revision
    undo_tx = editor.plan_edit(applied_doc, (0, 0), "undo", target_id="scratchpad:editor")
    assert undo_tx.status == "pending"
    assert undo_tx.can_apply is True
    undo_ok, restored_doc, undo_err = editor.apply_transaction(undo_tx, applied_doc)
    assert undo_ok is True
    assert restored_doc == initial_doc
    repeated_ok, repeated_doc, _ = editor.apply_transaction(undo_tx, restored_doc)
    assert repeated_ok is False
    assert repeated_doc == initial_doc


def test_forged_transaction_labels_cannot_authorize_external_input():
    """A caller-controlled target label is not proof of document ownership."""
    from types import SimpleNamespace

    engine = TransformsEngine()
    result = engine.transform_text("We basically finished.", "make_concise")
    engine._active_transaction = {"consumed": False}
    for target_type in ("scratchpad", "verified"):
        transaction = SimpleNamespace(target_type=target_type, consumed=False)
        with patch.object(TextInjector, "inject_with_status", side_effect=AssertionError("Unexpected external dispatch")), \
             patch.object(TextInjector, "inject_unicode_sendinput", side_effect=AssertionError("Unexpected fallback")):
            applied = engine.replace_selection(
                result.candidate_text, target_hwnd=12345,
                result=result, transaction=transaction,
            )
            reverted = engine.revert_last_transform(target_hwnd=12345, transaction=transaction)
        assert applied.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE
        assert reverted.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE


def test_external_mutation_controls_remain_disabled_after_preview():
    """Successful formatting enables copying, not an unsupported external edit."""
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QPushButton
    from ui.transforms_view import TransformsView

    app = QApplication.instance() or QApplication([])
    view = TransformsView()
    try:
        view.edit_original.setPlainText("We basically finished.")
        view._execute_preset("make_concise")
        assert view._current_result.can_apply is True
        assert view.btn_replace.isEnabled() is False
        buttons = view.findChildren(QPushButton)
        assert next(button for button in buttons if "Revert" in button.text()).isEnabled() is False
        assert next(button for button in buttons if "Copy Output" in button.text()).isEnabled() is True
        assert "unavailable" in view.lbl_external_edit.text().lower()
    finally:
        view.close()
        view.deleteLater()
        app.processEvents()


def test_unicode_fallback_refuses_unknown_foreground_before_dispatch():
    """Direct typing rechecks focus and leaves recovery text in memory."""
    import ctypes
    import engine.text_injector as injector_module
    for foreground in (0, 99999):
        with patch.object(injector_module, "HAS_WIN32", True), \
             patch.object(injector_module.sys, "platform", "win32"), \
             patch.object(injector_module.win32gui, "IsWindow", return_value=False), \
             patch.object(TextInjector, "_resolve_verified_foreground", return_value=(False, foreground, "Focus unavailable")), \
             patch.object(ctypes.windll.user32, "SendInput", side_effect=AssertionError("Unexpected typing")):
            assert TextInjector.inject_unicode_sendinput("Recovery text", target_hwnd=12345) is False
            assert TextInjector.last_injected_text == "Recovery text"


def test_unicode_fallback_rechecks_focus_after_preparing_input():
    """A focus change during input preparation prevents the actual SendInput."""
    import ctypes
    import engine.text_injector as injector_module
    with patch.object(injector_module, "HAS_WIN32", True), \
         patch.object(injector_module.sys, "platform", "win32"), \
         patch.object(injector_module.win32gui, "IsWindow", return_value=False), \
         patch.object(TextInjector, "_resolve_verified_foreground", side_effect=[(True, 12345, ""), (False, 99999, "Focus changed")]), \
         patch.object(ctypes.windll.user32, "SendInput", side_effect=AssertionError("Unexpected typing")):
        assert TextInjector.inject_unicode_sendinput("Recovery text", target_hwnd=12345) is False
        assert TextInjector.last_injected_text == "Recovery text"


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
    test_guarded_injector_refuses_after_focus_loss_no_unicode_fallback()
    test_missing_closed_or_changed_target_refuses_preserves_recovery()
    test_sent_unverified_retains_outcome_no_confirmed_message()
    test_external_mutation_without_verifiable_transaction_refuses()
    test_selection_or_document_changed_after_planning_refuses()
    test_revert_invoked_twice_refuses_second_call()
    test_clipboard_changed_by_user_during_abort_preserved()
    test_scratchpad_edit_and_undo_transactions_still_work()
    test_forged_transaction_labels_cannot_authorize_external_input()
    test_external_mutation_controls_remain_disabled_after_preview()
    test_unicode_fallback_refuses_unknown_foreground_before_dispatch()
    test_unicode_fallback_rechecks_focus_after_preparing_input()
    print("[RESULT] Honest Transforms tests PASSED (20/20).")
    sys.exit(0)
