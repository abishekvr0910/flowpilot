"""External rewrite entry points refuse input until revision checks exist."""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.selection_rewriter import SelectionRewriter, RewriteTransaction
from engine.orchestrator import FlowOrchestrator


class TestSelectionRewriter(unittest.TestCase):
    def setUp(self):
        self.transforms = MagicMock()
        self.rewriter = SelectionRewriter(self.transforms)

    def test_intent_classification_remains_available_for_preview(self):
        for spoken, intent in (("make this concise", "make_concise"),
                               ("fix grammar", "fix_grammar"), ("undo", "undo"),
                               ("hello world", "direct_replacement")):
            with self.subTest(spoken=spoken):
                self.assertEqual(self.rewriter.classify_intent(spoken)[0], intent)

    def test_supplied_selection_cannot_authorize_external_mutation(self):
        with patch("engine.text_injector.TextInjector.inject_with_status") as inject:
            for command in ("make this concise", "replacement", "undo"):
                with self.subTest(command=command):
                    result = self.rewriter.process_and_rewrite(command, "original", 1234)
                    self.assertEqual(result.status, "unsupported")
                    self.assertFalse(result.can_undo)
                    self.assertIsNone(result.transaction_id)
            inject.assert_not_called()
            self.transforms.transform_text.assert_not_called()

    def test_no_implicit_clipboard_capture(self):
        self.assertEqual(self.rewriter.capture_selection(), (None, 0, "", ""))
        self.assertEqual(self.rewriter.process_and_rewrite("replace it").status, "unsupported")
        self.transforms.get_selected_text_from_active_window.assert_not_called()

    def test_stale_undo_transaction_never_pastes_at_current_cursor(self):
        self.rewriter._undo_stack.append(RewriteTransaction(
            "legacy", 1234, "Editor", "notepad.exe", "original", "replacement", "edit", "custom"
        ))
        with patch("engine.text_injector.TextInjector.inject_with_status") as inject:
            self.assertFalse(self.rewriter.undo_last_rewrite(expected_hwnd=1234))
            inject.assert_not_called()

    def test_orchestrator_rejects_rewrite_before_startup_side_effects(self):
        orchestrator = FlowOrchestrator.__new__(FlowOrchestrator)
        self.assertFalse(orchestrator.start_selection_rewrite())
        self.assertFalse(orchestrator.start_dictation(is_selection_rewrite=True, pre_selected_text="old"))

    def test_undo_hotkey_explains_refusal_without_delegating(self):
        orchestrator = FlowOrchestrator.__new__(FlowOrchestrator)
        orchestrator.state = "idle"
        orchestrator._notify = MagicMock()
        orchestrator.selection_rewriter = MagicMock()
        self.assertFalse(orchestrator.undo_last_rewrite())
        orchestrator.selection_rewriter.undo_last_rewrite.assert_not_called()
        self.assertIn("unavailable", orchestrator._notify.call_args.args[1]["notice"])

    def test_transforms_hotkey_opens_preview_without_recording(self):
        from desktop_app import FlowPilotApp
        app = FlowPilotApp.__new__(FlowPilotApp)
        app.dashboard = MagicMock()
        app.orchestrator = MagicMock()
        with patch("engine.transforms_engine.get_transforms_engine") as getter:
            getter.return_value.get_selected_text_from_active_window.return_value = "selected"
            app._on_transforms_hotkey()
        app.dashboard.open_transforms.assert_called_once_with("selected")
        app.orchestrator.start_selection_rewrite.assert_not_called()


if __name__ == "__main__":
    unittest.main()
