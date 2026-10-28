"""
Tests for FlowPilot Universal Selection-Aware In-Place Text Rewriter (WP-2)
Validates intent classification, target safety blocking, FactGuard protection,
atomic replacement, focus shift abort, and undo rollback.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.selection_rewriter import SelectionRewriter, RewriteResult, RewriteTransaction
from engine.text_injector import InjectionResult, InjectionStatus


class TestSelectionRewriter(unittest.TestCase):

    def setUp(self):
        self.rewriter = SelectionRewriter()

    def test_intent_classification(self):
        """Validates regex classification of spoken editing intents."""
        cases = [
            ("make this concise", "make_concise"),
            ("please make it shorter", "make_concise"),
            ("summarize this", "make_concise"),
            ("make this professional", "professional"),
            ("executive tone", "professional"),
            ("make this casual", "casual"),
            ("format as bullet points", "bullet_points"),
            ("bullet list", "bullet_points"),
            ("fix grammar", "fix_grammar"),
            ("correct typos", "fix_grammar"),
            ("translate this to english", "translate_en"),
            ("undo", "undo"),
            ("revert that edit", "undo"),
            ("replace Friday with Monday", "custom_instruction"),
            ("We need to deploy immediately", "direct_replacement"),
        ]

        for spoken, expected_intent in cases:
            intent, _ = SelectionRewriter.classify_intent(spoken)
            self.assertEqual(intent, expected_intent, f"Failed on input: '{spoken}'")

    def test_target_safety_blocking(self):
        """Asserts that terminal windows and credential fields are blocked."""
        # Terminal process test
        with patch("engine.text_injector.TextInjector.get_target_window_info",
                   return_value=(1001, "Windows PowerShell", "powershell.exe")):
            res = self.rewriter.process_and_rewrite(
                spoken_command="make this concise",
                selected_text="Some text",
                target_hwnd=1001
            )
            self.assertEqual(res.status, "blocked_safety")
            self.assertIn("terminal", res.error_message.lower())

        # Credential window test
        with patch("engine.text_injector.TextInjector.get_target_window_info",
                   return_value=(1002, "1Password - Vault Master", "1password.exe")):
            res = self.rewriter.process_and_rewrite(
                spoken_command="make this concise",
                selected_text="secret password text",
                target_hwnd=1002
            )
            self.assertEqual(res.status, "blocked_safety")
            self.assertIn("secure credentials", res.error_message.lower())

    def test_focus_shift_abort(self):
        """Asserts that a focus shift before injection aborts safely and stages to recovery buffer."""
        original_text = "The quarterly revenue was $15,000 across 3 products."

        # Simulate focus shifting to HWND 9999 immediately prior to injection
        with patch("engine.text_injector.TextInjector.get_target_window_info",
                   return_value=(9999, "Other Window", "chrome.exe")):
            res = self.rewriter.process_and_rewrite(
                spoken_command="make this concise",
                selected_text=original_text,
                target_hwnd=1234  # Originally captured from 1234
            )
            self.assertEqual(res.status, "aborted_focus")
            self.assertIn("focus changed", res.error_message.lower())

    def test_factguard_preservation(self):
        """Asserts FactGuard vetoes any transform that modifies critical numbers or negations."""
        original_text = "Do not deploy on Friday, the cost is $500."

        # Mock transforms_engine to corrupt the number ($500 -> $50)
        mock_result = MagicMock()
        mock_result.can_apply = True
        mock_result.status = "success"
        mock_result.candidate_text = "Do not deploy on Friday, the cost is $50."  # Corrupted number!
        mock_result.guard_status = "passed"

        with patch.object(self.rewriter.transforms_engine, "transform_text", return_value=mock_result):
            with patch("engine.text_injector.TextInjector.get_target_window_info",
                       return_value=(5555, "Editor Window", "notepad.exe")):
                res = self.rewriter.process_and_rewrite(
                    spoken_command="make this concise",
                    selected_text=original_text,
                    target_hwnd=5555
                )
                self.assertEqual(res.status, "blocked_factguard")
                self.assertIn("factguard", res.error_message.lower())

    def test_successful_rewrite_and_undo(self):
        """Tests successful atomic replacement and subsequent undo restoration."""
        original_text = "In my opinion, we really ought to deploy the build."
        expected_concise = "We ought to deploy the build."

        mock_inject = MagicMock(return_value=InjectionResult(
            status=InjectionStatus.CONFIRMED_INSERTED,
            target_hwnd=7777
        ))

        with patch("engine.text_injector.TextInjector.get_target_window_info",
                   return_value=(7777, "Document - Notepad", "notepad.exe")):
            with patch("engine.text_injector.TextInjector.inject_with_status", mock_inject):
                # 1. Execute rewrite
                res = self.rewriter.process_and_rewrite(
                    spoken_command="make this concise",
                    selected_text=original_text,
                    target_hwnd=7777
                )
                self.assertEqual(res.status, "applied")
                self.assertTrue(res.can_undo)
                self.assertIsNotNone(res.transaction_id)
                self.assertEqual(len(self.rewriter._undo_stack), 1)

                # Verify inject_with_status was called with replacement
                self.assertEqual(mock_inject.call_count, 1)

                # 2. Execute Undo
                undo_ok = self.rewriter.undo_last_rewrite(expected_hwnd=7777)
                self.assertTrue(undo_ok)
                self.assertEqual(len(self.rewriter._undo_stack), 0)
                # Verify inject_with_status was called second time with original_text
                self.assertEqual(mock_inject.call_count, 2)
                second_call_args = mock_inject.call_args_list[1]
                self.assertEqual(second_call_args[0][0], original_text)


if __name__ == "__main__":
    unittest.main()
