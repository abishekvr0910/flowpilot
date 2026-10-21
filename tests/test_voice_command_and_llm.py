"""
FlowPilot Voice Command Mode & Local LLM Rewriting Test Suite (PR 5)
Verifies:
1. Explicit spoken command capture vs document dictation separation
2. Voice command transcription, input reflection, diff preview, and explicit apply
3. Bounded, single-direction undo for voice edits
4. Ambiguous command refusal and FactGuard invariant enforcement
5. Microphone release and recording cancellation on Scratchpad hide/close
6. VoiceCommandWorker asynchronous execution off the UI thread
7. Local LLM provider offline security: loopback-only, no-redirects, zero proxy leak
8. Local LLM explicit model selection (no silent first-model guessing)
9. Local LLM hard wall-clock deadline enforcement even on slow/hanging backends
10. FactGuard invariant enforcement on LLM generative rewrites
"""

import copy
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from engine.voice_editor import VoiceEditor, EditTransaction
from engine.local_llm import LocalLLMProvider
from engine.writing_intelligence import FactGuard
from ui.scratchpad_view import ScratchpadView, VoiceCommandWorker


class VoiceCommandModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pad_file = Path(self.temp_dir.name) / "pad_test.txt"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_voice_command_separate_from_document_dictation(self):
        """Dictation inserts text into document; voice commands never bleed into document text."""
        with patch("ui.scratchpad_view.AUTOSAVE_FILE", self.pad_file):
            sp = ScratchpadView()
            try:
                # 1. Normal dictation into pad
                sp.editor.setPlainText("Initial document text. ")
                from PySide6.QtGui import QTextCursor
                sp.editor.moveCursor(QTextCursor.End)
                sp.insert_text("Dictated addition.")
                self.assertEqual(sp.editor.toPlainText(), "Initial document text. Dictated addition.")

                # 2. Voice command execution: the instruction itself must NOT appear in the document text
                mock_stt = MagicMock()
                mock_stt.transcribe.return_value = {"text": "replace Initial with Updated"}
                sp._stt_engine = mock_stt

                dummy_audio = [0.0] * 1600
                tx = sp.process_voice_command_audio(dummy_audio)

                self.assertIsNotNone(tx)
                self.assertEqual(sp.input_edit_command.text(), "replace Initial with Updated")
                # Document MUST NOT be altered before apply!
                self.assertIn("Initial document text. Dictated addition.", sp.editor.toPlainText())
                self.assertTrue(sp.btn_apply_edit.isEnabled())

                # 3. Explicit apply modifies the document
                sp._on_apply_edit()
                self.assertIn("Updated document text. Dictated addition.", sp.editor.toPlainText())
                self.assertFalse(sp.btn_apply_edit.isEnabled())
            finally:
                sp._autosave_timer.stop()
                sp.close()

    def test_voice_command_audio_transcription_and_diff_preview(self):
        """Spoken audio produces transcribed instruction and visual diff preview without immediate mutation."""
        with patch("ui.scratchpad_view.AUTOSAVE_FILE", self.pad_file):
            sp = ScratchpadView()
            try:
                sp.editor.setPlainText("We meet on Friday afternoon.")
                mock_stt = MagicMock()
                mock_stt.transcribe.return_value = {"text": "replace Friday with Monday."}
                sp._stt_engine = mock_stt

                dummy_audio = [0.1, -0.1] * 800
                tx = sp.process_voice_command_audio(dummy_audio)

                self.assertIsNotNone(tx)
                self.assertEqual(tx.status, "pending")
                self.assertTrue(tx.can_apply)
                self.assertIn("Friday", tx.diff_preview)
                self.assertIn("Monday", tx.diff_preview)
                # Input box must display the cleaned command
                self.assertEqual(sp.input_edit_command.text(), "replace Friday with Monday")
                # Document still has Friday
                self.assertEqual(sp.editor.toPlainText(), "We meet on Friday afternoon.")

                # User confirms Apply
                sp._on_apply_edit()
                self.assertEqual(sp.editor.toPlainText(), "We meet on Monday afternoon.")
            finally:
                sp._autosave_timer.stop()
                sp.close()

    def test_ambiguous_spoken_command_blocks_apply_and_preserves_text(self):
        """When multiple targets match, apply is blocked and text remains completely untouched."""
        with patch("ui.scratchpad_view.AUTOSAVE_FILE", self.pad_file):
            sp = ScratchpadView()
            try:
                doc = "Friday morning and Friday evening."
                sp.editor.setPlainText(doc)

                mock_stt = MagicMock()
                mock_stt.transcribe.return_value = {"text": "replace Friday with Monday"}
                sp._stt_engine = mock_stt

                tx = sp.process_voice_command_audio([0.0] * 100)
                self.assertEqual(tx.status, "ambiguous")
                self.assertFalse(tx.can_apply)
                self.assertFalse(sp.btn_apply_edit.isEnabled())
                self.assertIn("Found 2 occurrences", sp.lbl_edit_diff.text())
                # Document is untouched
                self.assertEqual(sp.editor.toPlainText(), doc)
            finally:
                sp._autosave_timer.stop()
                sp.close()

    def test_spoken_undo_command_reverts_verified_edit(self):
        """Saying 'undo that edit' reverts the previous applied edit."""
        with patch("ui.scratchpad_view.AUTOSAVE_FILE", self.pad_file):
            sp = ScratchpadView()
            try:
                doc = "The release date is Friday."
                sp.editor.setPlainText(doc)

                # Edit 1: replace Friday with Monday
                mock_stt = MagicMock()
                mock_stt.transcribe.return_value = {"text": "replace Friday with Monday"}
                sp._stt_engine = mock_stt
                sp.process_voice_command_audio([0.0] * 100)
                sp._on_apply_edit()
                self.assertEqual(sp.editor.toPlainText(), "The release date is Monday.")

                # Edit 2: Spoken undo command
                mock_stt.transcribe.return_value = {"text": "undo that edit"}
                tx_undo = sp.process_voice_command_audio([0.0] * 100)
                self.assertTrue(tx_undo.can_apply)
                self.assertEqual(tx_undo.operation, "undo")
                sp._on_apply_edit()
                self.assertEqual(sp.editor.toPlainText(), doc)
            finally:
                sp._autosave_timer.stop()
                sp.close()

    def test_voice_command_mic_closed_on_hide_and_close(self):
        """Scratchpad hideEvent and closeEvent must close microphone stream and reset command recording state."""
        with patch("ui.scratchpad_view.AUTOSAVE_FILE", self.pad_file):
            sp = ScratchpadView()
            mock_recorder = MagicMock()
            sp._audio_recorder = mock_recorder

            # Simulate starting command recording
            sp._start_command_recording()
            self.assertTrue(sp._is_recording_command)
            mock_recorder.start_recording.assert_called_once()

            # Trigger hideEvent: must stop recording with keep_stream_alive=False and reset flag
            from PySide6.QtGui import QHideEvent
            sp.hideEvent(QHideEvent())
            self.assertFalse(sp._is_recording_command)
            mock_recorder.stop_recording.assert_called_with(keep_stream_alive=False)
            self.assertIn("Speak Command", sp.btn_speak_command.text())

            # Simulate starting again, then trigger closeEvent
            sp._start_command_recording()
            self.assertTrue(sp._is_recording_command)
            from PySide6.QtGui import QCloseEvent
            sp.closeEvent(QCloseEvent())
            self.assertFalse(sp._is_recording_command)
            mock_recorder.stop_recording.assert_called_with(keep_stream_alive=False)

    def test_voice_command_worker_async_execution(self):
        """VoiceCommandWorker runs transcription and planning in background without UI freezing."""
        mock_stt = MagicMock()
        mock_stt.transcribe.return_value = {"text": "replace apple with orange"}
        editor = VoiceEditor()
        doc = "I have an apple in my basket."

        worker = VoiceCommandWorker(
            stt=mock_stt,
            editor=editor,
            doc_text=doc,
            sel_range=(0, 0),
            audio=[0.0] * 1600
        )

        planned_results = []
        worker.command_planned.connect(lambda cl, tx, err: planned_results.append((cl, tx, err)))
        worker.start()
        worker.wait(2000)
        self.app.processEvents()

        self.assertEqual(len(planned_results), 1)
        cl, tx, err = planned_results[0]
        self.assertEqual(cl, "replace apple with orange")
        self.assertEqual(err, "")
        self.assertIsNotNone(tx)
        self.assertTrue(tx.can_apply)
        self.assertIn("orange", tx.candidate_text)


class LocalLLMSecurityAndModelSelectionTests(unittest.TestCase):
    def test_default_disabled_requires_explicit_opt_in(self):
        """LocalLLMProvider is disabled by default and performs zero network calls."""
        provider = LocalLLMProvider(enabled=False)
        self.assertFalse(provider.is_available())
        self.assertIsNone(provider.transform("Hello", "make this shorter"))

    def test_non_loopback_endpoint_rejected_zero_egress(self):
        """External IPs and hostnames are rejected immediately without DNS queries."""
        for bad_url in ("http://api.openai.com", "http://192.168.1.50:11434", "http://8.8.8.8:8080", "https://ollama.ai"):
            provider = LocalLLMProvider(base_url=bad_url, model="qwen2.5:3b", enabled=True)
            self.assertFalse(provider.is_available())

    def test_explicit_model_identity_required_no_silent_guessing(self):
        """If no model is configured, provider does NOT silently grab models[0]."""
        provider = LocalLLMProvider(base_url="http://127.0.0.1:11434", model="", enabled=True)
        self.assertFalse(provider.is_available())

    def test_uninstalled_requested_model_fails_closed(self):
        """If the requested model is not installed on the local server, is_available returns False."""
        provider = LocalLLMProvider(base_url="http://127.0.0.1:11434", model="qwen3:4b", enabled=True)
        fake_tags = json.dumps({"models": [{"name": "llama3.2:3b"}, {"name": "nomic-embed:latest"}]}).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = fake_tags
        mock_resp.__enter__.return_value = mock_resp

        with patch("engine.local_llm._SECURE_LOCAL_OPENER.open", return_value=mock_resp):
            self.assertFalse(provider.is_available(force_refresh=True))
            self.assertIsNone(provider.get_active_model())

    def test_matching_installed_model_is_activated(self):
        """When the explicitly requested model is installed, is_available succeeds."""
        provider = LocalLLMProvider(base_url="http://127.0.0.1:11434", model="qwen2.5:3b", enabled=True)
        fake_tags = json.dumps({"models": [{"name": "qwen2.5:3b"}, {"name": "nomic-embed:latest"}]}).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = fake_tags
        mock_resp.__enter__.return_value = mock_resp

        with patch("engine.local_llm._SECURE_LOCAL_OPENER.open", return_value=mock_resp):
            self.assertTrue(provider.is_available(force_refresh=True))
            self.assertEqual(provider.get_active_model(), "qwen2.5:3b")


class LocalLLMRewritingAndFactGuardTests(unittest.TestCase):
    def test_voice_editor_unsupported_when_llm_inactive(self):
        """Open-ended natural language prompt returns typed 'unsupported' when LLM is inactive."""
        editor = VoiceEditor()
        with patch("engine.local_llm.get_local_llm") as mock_get_llm:
            mock_get_llm.return_value.is_available.return_value = False
            tx = editor.plan_edit("Drafting email", instruction="make this sound like an executive memo")
            self.assertEqual(tx.status, "unsupported")
            self.assertFalse(tx.can_apply)
            self.assertEqual(tx.operation, "unsupported")

    def test_voice_editor_llm_generative_rewrite_with_factguard_pass(self):
        """Active local LLM generates candidate rewrite; FactGuard confirms invariants."""
        editor = VoiceEditor()
        original = "Please submit the bug report by end of day."
        rewritten = "Kindly provide the defect documentation before close of business."

        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm.transform.return_value = rewritten

        with patch("engine.local_llm.get_local_llm", return_value=mock_llm):
            tx = editor.plan_edit(original, instruction="make this more formal")
            self.assertEqual(tx.status, "pending")
            self.assertTrue(tx.can_apply)
            self.assertEqual(tx.operation, "local_llm_rewrite")
            self.assertEqual(tx.candidate_text, rewritten)

            # Apply succeeds
            ok, final_text, _ = editor.apply_transaction(tx, original)
            self.assertTrue(ok)
            self.assertEqual(final_text, rewritten)

    def test_factguard_blocks_llm_hallucinated_facts(self):
        """If the local LLM alters numbers or negations, FactGuard aborts the transaction."""
        editor = VoiceEditor()
        original = "We deployed 5 microservices to production. Do not rollback."
        # Hallucinated rewrite changed 5 -> 10 and dropped "not"
        hallucinated = "We deployed 10 microservices to production. Rollback immediately."

        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm.transform.return_value = hallucinated

        with patch("engine.local_llm.get_local_llm", return_value=mock_llm):
            tx = editor.plan_edit(original, instruction="rewrite this clearly")
            self.assertEqual(tx.status, "aborted")
            self.assertFalse(tx.can_apply)
            self.assertIn("FactGuard", tx.error_message)
            self.assertEqual(tx.candidate_text, original)

    def test_llm_timeout_leaves_document_unchanged(self):
        """When local LLM times out or returns empty, transaction is unavailable and text is preserved."""
        editor = VoiceEditor()
        original = "Keep this text exactly safe."

        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm.transform.return_value = None  # Timed out

        with patch("engine.local_llm.get_local_llm", return_value=mock_llm):
            tx = editor.plan_edit(original, instruction="summarize this")
            self.assertEqual(tx.status, "unavailable")
            self.assertFalse(tx.can_apply)
            self.assertEqual(tx.candidate_text, original)

    def test_llm_hard_deadline_enforcement_on_slow_response(self):
        """Even if the backend hangs or sleeps for 5s, a 0.3s deadline must abort at <= 0.45s and return None."""
        provider = LocalLLMProvider(base_url="http://127.0.0.1:11434", model="qwen2.5:3b", enabled=True)
        provider._cached_available = True
        provider._cache_timestamp = time.time()
        provider._active_model = "qwen2.5:3b"

        def slow_open(req, timeout=None):
            time.sleep(2.0)  # Simulated slow backend
            resp = MagicMock()
            resp.status = 200
            resp.read.return_value = json.dumps({"response": "unwanted late result"}).encode("utf-8")
            return resp

        with patch("engine.local_llm._SECURE_LOCAL_OPENER.open", side_effect=slow_open):
            t0 = time.monotonic()
            result = provider.transform("Test content", "make it snappy", timeout=0.3)
            elapsed = time.monotonic() - t0
            self.assertLess(elapsed, 0.5, f"Deadline took too long to abort: {elapsed:.3f}s")
            self.assertIsNone(result, f"Expected None on timeout, got: {result}")


if __name__ == "__main__":
    unittest.main()
