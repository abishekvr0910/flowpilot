"""Adversarial, hardware-free checks for the PR 2/3/4 and companion handoff."""
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.voice_editor import VoiceEditor
from engine.evaluation_metrics import verify_critical_facts
from engine.prompt_budget import PromptBudgetManager


class EditSafetyTests(unittest.TestCase):
    def test_target_mismatch_rejects_edit(self):
        editor = VoiceEditor()
        tx = editor.plan_edit("Friday", instruction="replace Friday with Monday", target_id="pad:a")
        self.assertFalse(editor.apply_transaction(tx, "Friday", current_target_id="pad:b")[0])

    def test_new_preview_supersedes_old_preview(self):
        editor = VoiceEditor()
        old = editor.plan_edit("Friday", instruction="replace Friday with Monday")
        editor.plan_edit("Friday", instruction="replace Friday with Tuesday")
        self.assertFalse(editor.apply_transaction(old, "Friday")[0])

    def test_cancelled_preview_cannot_apply_saved_copy(self):
        editor = VoiceEditor()
        tx = editor.plan_edit("Friday", instruction="replace Friday with Monday")
        editor.cancel_transaction(tx.transaction_id)
        self.assertFalse(editor.apply_transaction(tx, "Friday")[0])

    def test_selection_change_rejects_edit(self):
        editor = VoiceEditor()
        doc = "Friday and Monday"
        tx = editor.plan_edit(doc, (0, 6), "replace Friday with Tuesday")
        ok, result, _ = editor.apply_transaction(tx, doc, (11, 17))
        self.assertFalse(ok)
        self.assertEqual(result, doc)

    def test_copied_transaction_cannot_replay(self):
        editor = VoiceEditor()
        tx = editor.plan_edit("Friday", instruction="replace Friday with Monday")
        replay = copy.deepcopy(tx)
        self.assertTrue(editor.apply_transaction(tx, "Friday")[0])
        self.assertFalse(editor.apply_transaction(replay, "Friday")[0])

    def test_mutated_candidate_cannot_apply(self):
        editor = VoiceEditor()
        tx = editor.plan_edit("Friday. Do not deploy.", instruction="replace Friday with Monday")
        tx.candidate_text = "Monday. Deploy."
        self.assertFalse(editor.apply_transaction(tx, tx.original_text)[0])

    def test_preset_cannot_bypass_failed_factguard(self):
        editor = VoiceEditor()
        with patch("engine.transforms_engine.TransformsEngine._apply_concise", return_value="Deploy."):
            tx = editor.plan_edit("Do not deploy.", instruction="make this shorter")
        self.assertFalse(editor.apply_transaction(tx, "Do not deploy.")[0])

    def test_invalid_selection_rejected_not_clamped(self):
        tx = VoiceEditor().plan_edit("Keep this.", (-5, 500), "remove this part")
        self.assertFalse(tx.can_apply)

    def test_external_target_is_not_enabled_by_default(self):
        tx = VoiceEditor().plan_edit("Friday", instruction="replace Friday with Monday", target_type="external")
        self.assertFalse(tx.can_apply)

    def test_undo_walks_back_history_not_toggles(self):
        editor = VoiceEditor()
        doc = "Version one"
        for instruction in ("replace one with two", "replace two with three", "undo that edit", "undo that edit"):
            tx = editor.plan_edit(doc, instruction=instruction)
            ok, doc, error = editor.apply_transaction(tx, doc)
            self.assertTrue(ok, error)
        self.assertEqual(doc, "Version one")


class EvaluationSafetyTests(unittest.TestCase):
    def test_missing_manifest_is_error_not_fallback(self):
        from benchmarks.run_real_voice_eval import run_evaluation
        with self.assertRaises(FileNotFoundError):
            run_evaluation(ROOT / "scratch/not-a-real-manifest.json")

    def test_recorded_audio_requires_explicit_consent(self):
        from engine.real_voice_corpus import CorpusItem, RealVoiceCorpus
        item = CorpusItem("one", "en", "clean", "hello", "Hello.", "speaker", audio_file="one.wav")
        self.assertFalse(RealVoiceCorpus([item]).validate_integrity()[0])

    def test_real_audio_path_uses_recognizer_not_reference(self):
        from benchmarks.run_real_voice_eval import run_evaluation
        from engine.real_voice_corpus import CorpusItem, RealVoiceCorpus
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "clip.wav").write_bytes(b"fixture at mocked hardware boundary")
            item = CorpusItem("one", "en", "clean", "hello world", "Hello world.", "speaker",
                              consent_verified=True, audio_file="clip.wav")
            RealVoiceCorpus([item]).save_manifest(root / "manifest.json")
            with patch("benchmarks.run_real_voice_eval.STTEngine") as loader, patch(
                    "benchmarks.run_real_voice_eval.ContextProcessor") as processor:
                loader.return_value.transcribe.return_value = {"text": "hello planet"}
                processor.return_value.process.return_value = "Hello planet."
                report = run_evaluation(root / "manifest.json", output_report=root / "report.json")
                self.assertEqual(report["languages"]["en"]["avg_wer"], 0.5)
                self.assertEqual(report["evaluated_items"], 1)
                loader.return_value.transcribe.assert_called_once()
                self.assertNotIn("hypothesis", json.loads((root / "report.json").read_text())["trials"][0])
                loader.return_value.transcribe.side_effect = RuntimeError("private words")
                report = run_evaluation(root / "manifest.json")
                self.assertEqual(report["failed_items"], 1)
                self.assertEqual(report["evaluated_items"], 0)
                self.assertIsNone(report["languages"]["en"]["avg_wer"])

    def test_number_substring_is_not_preservation(self):
        self.assertFalse(verify_critical_facts("Use 12 workers", "Use 120 workers")["preserved"])

    def test_negation_substring_is_not_preservation(self):
        self.assertFalse(verify_critical_facts("Do not deploy", "Use notebook to deploy")["preserved"])

    def test_duplicate_and_added_entities_are_detected(self):
        self.assertFalse(verify_critical_facts("Use 5 then 5", "Use 5")["preserved"])
        self.assertFalse(verify_critical_facts("Deploy now", "Do not deploy now")["preserved"])

    def test_cli_flags_are_detected(self):
        self.assertFalse(verify_critical_facts("run --dry-run", "run --force")["preserved"])

    def test_missing_audio_never_scores_as_recognition(self):
        from benchmarks.run_real_voice_eval import run_evaluation
        with patch("benchmarks.run_real_voice_eval.STTEngine") as loader:
            report = run_evaluation(limit=1)
        self.assertEqual(report.get("evaluated_items"), 0)
        self.assertEqual(report.get("missing_audio_items"), 1)
        self.assertIsNone(report["languages"]["en"]["avg_wer"])
        loader.assert_not_called()


class BudgetSafetyTests(unittest.TestCase):
    def test_hotwords_cannot_escape_token_budget(self):
        tokenizer = SimpleNamespace(encode=lambda s, **kw: SimpleNamespace(ids=list(s)))
        hotwords = PromptBudgetManager.format_hotwords(["x" * 500, "valid"], max_tokens=20, tokenizer=tokenizer)
        self.assertEqual(hotwords, "valid")

    def test_live_polishing_honors_language_and_profile_scope(self):
        from engine.personalization import PersonalizationEngine
        from engine.writing_intelligence import WritingIntelligence
        with tempfile.TemporaryDirectory() as folder:
            personal = PersonalizationEngine(storage_path=Path(folder) / "personal.json")
            personal.dictionary = []
            personal.add_term("ScopedToken", alias="secret word", language="ta", profile="developer")
            writer = WritingIntelligence(personalization=personal)
            for lang, profile in (("en", "developer"), ("ta", "email"), ("auto", "developer")):
                output = writer.polish("secret word", mode="verbatim", language=lang, style=profile)["text"]
                self.assertEqual(output.lower(), "secret word")
            self.assertEqual(writer.polish("secret word", mode="verbatim", language="ta", style="developer")["text"], "ScopedToken")
            self.assertEqual(personal.get_scoped_entries(), [])

    def test_oversized_base_cannot_escape_budget(self):
        tokenizer = SimpleNamespace(encode=lambda s, **kw: SimpleNamespace(ids=list(s)))
        manager = PromptBudgetManager(tokenizer=tokenizer)
        prompt, count, _ = manager.build_bounded_prompt("en", "x" * 200, [], max_total_tokens=20)
        self.assertLessEqual(count, 20)
        self.assertLessEqual(len(prompt), 20)


class CompanionIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def render(self, state="listening", level=0, elapsed=100, reduced=False):
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtCore import QRectF
        from ui.companion_renderer import CompanionRenderer
        img = QImage(96, 96, QImage.Format_ARGB32)
        img.fill(0)
        painter = QPainter(img)
        try:
            CompanionRenderer.render(painter, QRectF(0, 0, 96, 96), "kiki", state,
                                     elapsed, level, "autumn", reduced)
        finally:
            painter.end()
        return hashlib.sha256(bytes(img.bits())).hexdigest()

    def test_kiki_is_selectable(self):
        from engine.companion_assets import BUILTIN_COMPANIONS
        self.assertIn("kiki", [item["id"] for item in BUILTIN_COMPANIONS])

    def test_listening_reacts_to_audio_not_just_time(self):
        self.assertNotEqual(self.render(level=0), self.render(level=1))

    def test_confirmation_settles_once(self):
        self.assertNotEqual(self.render("confirmed", elapsed=100), self.render("confirmed", elapsed=1300))
        self.assertEqual(self.render("confirmed", elapsed=1300), self.render("confirmed", elapsed=3000))

    def test_hud_routes_kiki_to_shared_renderer(self):
        from ui.floating_hud import FloatingHUD
        from ui.companion_renderer import CompanionRenderer
        hud = FloatingHUD()
        try:
            hud._visual_style = "kiki"
            with patch.object(CompanionRenderer, "render", wraps=CompanionRenderer.render) as render:
                hud.grab()
                self.assertEqual(render.call_args.kwargs["style"], "kiki")
                self.assertIn("state_elapsed_ms", render.call_args.kwargs)
        finally:
            hud.close()

    def test_scratchpad_handles_emoji_offsets_and_invalidates_preview(self):
        from ui.scratchpad_view import ScratchpadView
        from PySide6.QtGui import QTextCursor
        with tempfile.TemporaryDirectory() as folder, patch("ui.scratchpad_view.AUTOSAVE_FILE", Path(folder) / "pad.txt"):
            pad = ScratchpadView()
            try:
                pad.editor.setPlainText("😀 Friday and Friday")
                cursor = pad.editor.textCursor()
                cursor.setPosition(3)
                cursor.setPosition(9, QTextCursor.KeepAnchor)
                pad.editor.setTextCursor(cursor)
                tx = pad.execute_voice_command("replace Friday with Monday", auto_apply=True)
                self.assertEqual(tx.status, "applied")
                self.assertEqual(pad.editor.toPlainText(), "😀 Monday and Friday")
                pad.execute_voice_command("replace Monday with Tuesday")
                self.assertTrue(pad.btn_apply_edit.isEnabled())
                pad.input_edit_command.setText("remove this part")
                self.assertFalse(pad.btn_apply_edit.isEnabled())
                self.assertIsNone(pad.active_transaction)
            finally:
                pad._autosave_timer.stop()
                pad.close()

    def test_reduced_motion_preserves_state_but_stops_motion(self):
        for state in ("idle", "listening", "processing", "confirmed", "unverified", "recovery"):
            self.assertEqual(self.render(state, 0, 0, True), self.render(state, 1, 3500, True))
        self.assertNotEqual(self.render("unverified", reduced=True), self.render("confirmed", reduced=True))


if __name__ == "__main__":
    unittest.main()
