"""
FlowPilot PR 4 Acceptance Test Suite:
Bounded Voice Editing, Atomic EditTransactions, and Scratchpad Integration

Tests:
1. Unique span replacement ("replace Friday with Monday").
2. Zero matches handling (honest abort without guessing).
3. Ambiguity handling (multiple matches refuse to guess and request clarification).
4. Scoped replacement within explicit selection range.
5. Selection deletion ("remove this part") with and without selection.
6. Document appending ("add this sentence at the end").
7. Verified undo transactions tied to document revision hash.
8. Concurrent modification and one-use transaction ID guards.
9. Terminal and sensitive window safety checks.
10. In-app Scratchpad voice command integration.
"""

import sys
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from engine.voice_editor import VoiceEditor, EditTransaction
from ui.scratchpad_view import ScratchpadView


def test_unique_span_replacement():
    print("--- [1] Unique Span Replacement ('replace Friday with Monday') ---")
    ve = VoiceEditor()
    doc = "Our team sync is scheduled for Friday at 10am."

    tx = ve.plan_edit(doc, instruction="replace Friday with Monday")
    print(f"Planned tx: status={tx.status}, diff={tx.diff_preview}")
    assert tx.operation == "replace_span"
    assert tx.status == "pending"
    assert tx.can_apply is True
    assert "Friday" in tx.diff_preview and "Monday" in tx.diff_preview

    ok, new_doc, msg = ve.apply_transaction(tx, doc)
    assert ok is True
    assert new_doc == "Our team sync is scheduled for Monday at 10am."
    assert tx.consumed is True
    assert tx.status == "applied"
    print("[PASS] Unique span replaced cleanly.")


def test_zero_matches_aborts():
    print("--- [2] Zero Matches Honest Abort ---")
    ve = VoiceEditor()
    doc = "Release notes for version 3.10."

    tx = ve.plan_edit(doc, instruction="replace Saturday with Monday")
    print(f"Zero match tx: status={tx.status}, error={tx.error_message}")
    assert tx.status == "aborted"
    assert tx.can_apply is False
    assert "not found" in tx.error_message.lower()

    ok, out_doc, _ = ve.apply_transaction(tx, doc)
    assert ok is False
    assert out_doc == doc
    print("[PASS] Non-existent span correctly aborts without changing text.")


def test_ambiguity_multiple_matches():
    print("--- [3] Ambiguity Detection (Multiple Matches Refuse to Guess) ---")
    ve = VoiceEditor()
    doc = "Sprint review on Friday, and deployment retrospective on Friday."

    tx = ve.plan_edit(doc, instruction="replace Friday with Monday")
    print(f"Ambiguous tx: status={tx.status}, error={tx.error_message}")
    assert tx.status == "ambiguous"
    assert tx.can_apply is False
    assert "2 occurrences" in tx.error_message

    ok, out_doc, _ = ve.apply_transaction(tx, doc)
    assert ok is False
    assert out_doc == doc
    print("[PASS] Multiple matches rejected as ambiguous without guessing.")


def test_scoped_selection_replacement():
    print("--- [4] Scoped Replacement Within Explicit Selection ---")
    ve = VoiceEditor()
    doc = "Sprint review on Friday, and deployment retrospective on Friday."
    # Target only the second "Friday": index 56..62
    friday2_start = doc.rfind("Friday")
    friday2_end = friday2_start + len("Friday")

    tx = ve.plan_edit(doc, selected_range=(friday2_start, friday2_end), instruction="replace Friday with Monday")
    assert tx.status == "pending"
    assert tx.can_apply is True

    ok, new_doc, _ = ve.apply_transaction(tx, doc, current_selection=(friday2_start, friday2_end))
    assert ok is True
    # First Friday preserved, second Friday replaced
    assert new_doc == "Sprint review on Friday, and deployment retrospective on Monday."
    print("[PASS] Scoped selection replaced only targeted occurrence.")


def test_remove_selection():
    print("--- [5] Remove Selection ('remove this part') ---")
    ve = VoiceEditor()
    doc = "Sentence one. Sentence to delete. Sentence three."

    # A. Without selection: must abort honestly
    tx_nosel = ve.plan_edit(doc, selected_range=(0, 0), instruction="remove this part")
    print(f"No-selection tx: status={tx_nosel.status}, error={tx_nosel.error_message}")
    assert tx_nosel.status == "aborted"
    assert tx_nosel.can_apply is False
    assert "No text selected" in tx_nosel.error_message

    # B. With active selection
    span_start = doc.find("Sentence to delete. ")
    span_end = span_start + len("Sentence to delete. ")
    tx_sel = ve.plan_edit(doc, selected_range=(span_start, span_end), instruction="remove this part")
    assert tx_sel.status == "pending"
    assert tx_sel.can_apply is True

    ok, new_doc, _ = ve.apply_transaction(tx_sel, doc, current_selection=(span_start, span_end))
    assert ok is True
    assert new_doc == "Sentence one. Sentence three."
    print("[PASS] Selection removal requires and honors active selection.")


def test_append_at_end():
    print("--- [6] Append At End ('add this sentence at the end') ---")
    ve = VoiceEditor()
    doc = "First paragraph."

    tx = ve.plan_edit(doc, instruction="add this sentence at the end: Final summary point.")
    assert tx.operation == "append_text"
    assert tx.status == "pending"
    assert tx.can_apply is True

    ok, new_doc, _ = ve.apply_transaction(tx, doc)
    assert ok is True
    assert "Final summary point." in new_doc
    assert new_doc.startswith("First paragraph.")
    print("[PASS] Append at end adds text to document boundary.")


def test_verified_undo_and_concurrent_protection():
    print("--- [7] Verified Undo & Concurrent Modification Guard ---")
    ve = VoiceEditor()
    doc = "Version 1 text."

    # Plan and apply edit
    tx1 = ve.plan_edit(doc, instruction="replace Version 1 with Version 2")
    ok1, doc_v2, _ = ve.apply_transaction(tx1, doc)
    assert ok1 is True
    assert doc_v2 == "Version 2 text."

    # Undo while revision matches
    tx_undo = ve.plan_edit(doc_v2, instruction="undo that edit")
    assert tx_undo.status == "pending"
    assert tx_undo.can_apply is True

    ok_undo, doc_reverted, _ = ve.apply_transaction(tx_undo, doc_v2)
    assert ok_undo is True
    assert doc_reverted == doc
    print("Verified undo successfully restored initial text.")

    # Test concurrent modification guard
    tx2 = ve.plan_edit(doc_reverted, instruction="replace Version 1 with Version 3")
    concurrent_doc = "Version 1 text concurrently edited by user typing."
    ok_blocked, out_doc, err = ve.apply_transaction(tx2, concurrent_doc)
    assert ok_blocked is False
    assert out_doc == concurrent_doc
    assert "concurrently" in err.lower()
    print("Concurrent modification correctly blocked execution.")


def test_one_use_transaction_guard():
    print("--- [8] One-Use Transaction ID Guard ---")
    ve = VoiceEditor()
    doc = "Original text."
    tx = ve.plan_edit(doc, instruction="replace Original with Updated")

    ok1, doc1, _ = ve.apply_transaction(tx, doc)
    assert ok1 is True

    # Attempt second apply with same transaction object
    ok2, doc2, err = ve.apply_transaction(tx, doc1)
    assert ok2 is False
    assert "already been applied" in err
    print("[PASS] One-use transaction ID enforcement verified.")


def test_terminal_and_security_safeguards():
    print("--- [9] Terminal & Security Safeguards ---")
    # Terminal processes must be restricted
    safe_pwsh, err_pwsh = VoiceEditor.check_target_safety("powershell.exe", "Windows PowerShell")
    assert safe_pwsh is False
    assert "terminal" in err_pwsh.lower()

    safe_cmd, err_cmd = VoiceEditor.check_target_safety("cmd.exe", "Command Prompt")
    assert safe_cmd is False

    safe_wt, err_wt = VoiceEditor.check_target_safety("windowsterminal.exe", "Terminal")
    assert safe_wt is False

    # Password window check
    safe_pass, err_pass = VoiceEditor.check_target_safety("notepad.exe", "KeePass Password Safe")
    assert safe_pass is False
    assert "credentials" in err_pass.lower()

    # Normal application must pass
    safe_normal, err_normal = VoiceEditor.check_target_safety("notepad.exe", "meeting_notes.txt - Notepad")
    assert safe_normal is True
    assert err_normal is None
    print("[PASS] Terminal and security safeguards verified.")


def test_scratchpad_voice_command_integration():
    print("--- [10] In-App Scratchpad Voice Command Execution ---")
    sp = ScratchpadView()
    sp.editor.setPlainText("We will launch the product on Friday morning.")

    # Direct voice command execution into Scratchpad canvas
    tx = sp.execute_voice_command("replace Friday with Monday", auto_apply=True)
    assert tx.status == "applied"
    assert sp.editor.toPlainText() == "We will launch the product on Monday morning."

    # Undo voice command execution
    tx_undo = sp.execute_voice_command("undo that edit", auto_apply=True)
    assert tx_undo.status == "applied"
    assert sp.editor.toPlainText() == "We will launch the product on Friday morning."

    print("[PASS] ScratchpadView voice editing integration verified.")


def run_all_pr4_tests():
    print("=" * 70)
    print("       FLOWPILOT PR 4 BOUNDED VOICE EDITING TEST SUITE")
    print("=" * 70)
    test_unique_span_replacement()
    test_zero_matches_aborts()
    test_ambiguity_multiple_matches()
    test_scoped_selection_replacement()
    test_remove_selection()
    test_append_at_end()
    test_verified_undo_and_concurrent_protection()
    test_one_use_transaction_guard()
    test_terminal_and_security_safeguards()
    test_scratchpad_voice_command_integration()
    print("=" * 70)
    print("ALL PR 4 BOUNDED VOICE EDITING TESTS PASSED (10/10)!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_pr4_tests()
