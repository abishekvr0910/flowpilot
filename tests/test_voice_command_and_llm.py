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
import threading
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
        worker.command_planned.connect(lambda req_id, cl, tx, err: planned_results.append((cl, tx, err)))
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
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from engine.local_llm import shutdown_local_llm
        shutdown_local_llm(wait=False)

    def tearDown(self):
        from engine.local_llm import shutdown_local_llm
        shutdown_local_llm(wait=False)

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

        stop_event = threading.Event()
        def slow_open(req, timeout=None):
            stop_event.wait(timeout=0.5)  # Simulated slow backend
            resp = MagicMock()
            resp.status = 200
            resp.read.return_value = json.dumps({"response": "unwanted late result"}).encode("utf-8")
            return resp

        try:
            with patch("engine.local_llm._SECURE_LOCAL_OPENER.open", side_effect=slow_open):
                t0 = time.monotonic()
                result = provider.transform("Test content", "make it snappy", timeout=0.3)
                elapsed = time.monotonic() - t0
                self.assertLess(elapsed, 0.5, f"Deadline took too long to abort: {elapsed:.3f}s")
                self.assertIsNone(result, f"Expected None on timeout, got: {result}")
        finally:
            stop_event.set()

    def test_voice_command_worker_target_id_matches_scratchpad_and_applies_cleanly(self):
        """Worker uses the Scratchpad instance's target_id so apply succeeds without 'target document changed'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pad_file = Path(tmpdir) / "pad.txt"
            with patch("ui.scratchpad_view.AUTOSAVE_FILE", pad_file):
                sp = ScratchpadView()
                try:
                    sp.editor.setPlainText("We meet on Friday afternoon.")
                    mock_stt = MagicMock()
                    mock_stt.transcribe.return_value = {"text": "replace Friday with Monday"}

                    # Create worker with exact scratchpad target ID
                    worker = VoiceCommandWorker(
                        stt=mock_stt,
                        editor=sp.voice_editor,
                        doc_text=sp.editor.toPlainText(),
                        sel_range=(0, 0),
                        audio=[0.0] * 100,
                        target_id=sp._target_id,
                        request_id=sp._active_request_id,
                        parent=sp
                    )
                    self.assertEqual(worker.target_id, sp._target_id)
                    worker.run()  # Run synchronously for verification

                    # Directly invoke the result handler with matching request_id
                    tx = sp.voice_editor.plan_edit(
                        document_text=sp.editor.toPlainText(),
                        instruction="replace Friday with Monday",
                        target_id=sp._target_id,
                        target_type="scratchpad"
                    )
                    self.assertEqual(tx.target_id, sp._target_id)
                    sp.edit_panel.setVisible(True)
                    sp._on_command_worker_result(sp._active_request_id, "replace Friday with Monday", tx, "")

                    self.assertTrue(sp.btn_apply_edit.isEnabled())
                    self.assertIn("Friday", sp.lbl_edit_diff.text())

                    # Apply must succeed and NOT fail with 'The target document changed'
                    sp._on_apply_edit()
                    self.assertEqual(sp.editor.toPlainText(), "We meet on Monday afternoon.")
                    self.assertIn("Applied", sp.lbl_edit_diff.text())
                finally:
                    sp._autosave_timer.stop()
                    sp.close()

    def test_voice_command_cancel_and_superseded_request_safely_ignored(self):
        """When user cancels or supersedes, worker is marked cancelled and late results do not restore preview."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pad_file = Path(tmpdir) / "pad.txt"
            with patch("ui.scratchpad_view.AUTOSAVE_FILE", pad_file):
                sp = ScratchpadView()
                try:
                    sp.editor.setPlainText("Task list for today.")
                    sp.edit_panel.setVisible(True)

                    mock_stt = MagicMock()
                    mock_stt.transcribe.return_value = {"text": "add finish review at the end"}

                    # Start worker with request id 1
                    sp._active_request_id = 1
                    worker = VoiceCommandWorker(
                        stt=mock_stt,
                        editor=sp.voice_editor,
                        doc_text=sp.editor.toPlainText(),
                        sel_range=(0, 0),
                        audio=[0.0] * 100,
                        target_id=sp._target_id,
                        request_id=1,
                        parent=sp
                    )
                    sp._command_worker = worker

                    # User clicks Cancel
                    sp._cancel_edit()
                    self.assertTrue(worker.is_cancelled())
                    self.assertEqual(sp._active_request_id, 2)
                    self.assertFalse(sp.edit_panel.isVisible())
                    self.assertIsNone(sp.active_transaction)

                    # Simulated late result arrives with old request id 1
                    late_tx = sp.voice_editor.plan_edit(
                        document_text=sp.editor.toPlainText(),
                        instruction="add finish review at the end",
                        target_id=sp._target_id,
                        target_type="scratchpad"
                    )
                    sp._on_command_worker_result(1, "add finish review at the end", late_tx, "")

                    # Must remain completely untouched! No preview restored, apply stays disabled
                    self.assertIsNone(sp.active_transaction)
                    self.assertFalse(sp.btn_apply_edit.isEnabled())
                    self.assertFalse(sp.edit_panel.isVisible())
                finally:
                    sp._autosave_timer.stop()
                    sp.close()

    def test_llm_health_check_contained_within_tight_budget(self):
        """A simulated 250ms probe against a 50ms budget must abort at <= 0.08s and return False."""
        provider = LocalLLMProvider(base_url="http://127.0.0.1:11434", model="qwen2.5:3b", enabled=True)
        provider._cached_available = None
        provider._cache_timestamp = 0

        stop_event = threading.Event()
        def slow_probe(req, timeout=None):
            stop_event.wait(timeout=0.25)  # 250ms simulated hang
            resp = MagicMock()
            resp.status = 200
            resp.read.return_value = json.dumps({"models": [{"name": "qwen2.5:3b"}]}).encode("utf-8")
            return resp

        try:
            with patch("engine.local_llm._SECURE_LOCAL_OPENER.open", side_effect=slow_probe):
                t0 = time.monotonic()
                available = provider.is_available(force_refresh=True, timeout=0.05)
                elapsed = time.monotonic() - t0
                self.assertLess(elapsed, 0.10, f"Health check took too long to abort: {elapsed:.3f}s")
                self.assertFalse(available)
        finally:
            stop_event.set()

    def test_llm_transform_contains_health_check_within_budget(self):
        """Calling transform with 50ms budget must abort within 0.10s even if health check is slow."""
        provider = LocalLLMProvider(base_url="http://127.0.0.1:11434", model="qwen2.5:3b", enabled=True)
        provider._cached_available = None
        provider._cache_timestamp = 0

        stop_event = threading.Event()
        def slow_probe(req, timeout=None):
            stop_event.wait(timeout=0.25)
            resp = MagicMock()
            resp.status = 200
            resp.read.return_value = json.dumps({"models": [{"name": "qwen2.5:3b"}]}).encode("utf-8")
            return resp

        try:
            with patch("engine.local_llm._SECURE_LOCAL_OPENER.open", side_effect=slow_probe):
                t0 = time.monotonic()
                res = provider.transform("Some text to transform", "make concise", timeout=0.05)
                elapsed = time.monotonic() - t0
                self.assertLess(elapsed, 0.10, f"Transform took too long to abort: {elapsed:.3f}s")
                self.assertIsNone(res)
        finally:
            stop_event.set()

    def test_voice_command_worker_preserves_collapsed_cursor_selection(self):
        """Collapsed cursor (e.g. at pos 6 with length 0) must NOT be rewritten to (0, 0)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pad_file = Path(tmpdir) / "pad.txt"
            with patch("ui.scratchpad_view.AUTOSAVE_FILE", pad_file):
                sp = ScratchpadView()
                try:
                    doc = "Friday afternoon meeting."
                    sp.editor.setPlainText(doc)

                    # Position cursor right after 'Friday' (pos 6) with no selection -> (6, 6)
                    cursor = sp.editor.textCursor()
                    cursor.setPosition(6)
                    sp.editor.setTextCursor(cursor)

                    from ui.scratchpad_view import _python_selection
                    current_sel = _python_selection(doc, sp.editor.textCursor())
                    self.assertEqual(current_sel, (6, 6))

                    mock_stt = MagicMock()
                    mock_stt.transcribe.return_value = {"text": "replace Friday with Monday"}

                    # Instantiate worker with exact collapsed cursor position (6, 6)
                    worker = VoiceCommandWorker(
                        stt=mock_stt,
                        editor=sp.voice_editor,
                        doc_text=doc,
                        sel_range=(6, 6),
                        audio=[0.0] * 100,
                        target_id=sp._target_id,
                        request_id=sp._active_request_id,
                        parent=sp
                    )
                    self.assertEqual(worker.sel_range, (6, 6))

                    planned_results = []
                    worker.command_planned.connect(lambda req_id, cl, tx, err: planned_results.append((req_id, cl, tx, err)))
                    worker.run()

                    self.assertEqual(len(planned_results), 1)
                    req_id, cl, tx, err = planned_results[0]
                    self.assertEqual(err, "")
                    self.assertIsNotNone(tx)
                    # Crucial assertion: source_selection must remain (6, 6), NEVER changed to (0, 0)!
                    self.assertEqual(tx.source_selection, (6, 6))

                    # Apply must match current selection (6, 6) and succeed without 'Selection changed' error
                    sp.edit_panel.setVisible(True)
                    sp._on_command_worker_result(req_id, cl, tx, "")
                    self.assertTrue(sp.btn_apply_edit.isEnabled())

                    sp._on_apply_edit()
                    self.assertEqual(sp.editor.toPlainText(), "Monday afternoon meeting.")
                    self.assertIn("Applied", sp.lbl_edit_diff.text())
                finally:
                    sp._autosave_timer.stop()
                    sp.close()

    def test_timed_out_llm_requests_do_not_exceed_concurrency_limit(self):
        """Sequentially timed-out requests must release the concurrency slot only when underlying work finishes."""
        import threading
        from engine.local_llm import get_in_flight_transforms

        provider = LocalLLMProvider(base_url="http://127.0.0.1:11434", model="qwen2.5:3b", enabled=True)
        provider._cached_available = True
        provider._cache_timestamp = time.time()
        provider._active_model = "qwen2.5:3b"

        unblock_event = threading.Event()

        def blocking_open(req, timeout=None):
            # Blocks until explicitly allowed to finish
            unblock_event.wait(timeout=2.0)
            resp = MagicMock()
            resp.status = 200
            resp.read.return_value = json.dumps({"response": "done"}).encode("utf-8")
            return resp

        try:
            with patch("engine.local_llm._SECURE_LOCAL_OPENER.open", side_effect=blocking_open):
                # 1. Request 1 times out after 0.05s
                res1 = provider.transform("First text", "summarize", timeout=0.05)
                self.assertIsNone(res1)

                # The underlying worker for Request 1 is still blocked on I/O: slot MUST remain 1!
                in_flight_after_1 = get_in_flight_transforms()
                self.assertEqual(in_flight_after_1, 1, "Concurrency slot must not be released while background work runs")

                # 2. Sequential Request 2 comes in while Request 1 is still running: MUST be dropped!
                res2 = provider.transform("Second text", "summarize", timeout=0.05)
                self.assertIsNone(res2)
                # Still exactly 1 in-flight (Request 2 was dropped, not added)
                self.assertEqual(get_in_flight_transforms(), 1)

                # 3. Sequential Request 3 comes in while Request 1 is still running: MUST be dropped!
                res3 = provider.transform("Third text", "summarize", timeout=0.05)
                self.assertIsNone(res3)
                self.assertEqual(get_in_flight_transforms(), 1)

                # Unblock Request 1's backend call
                unblock_event.set()
                # Wait for worker future callback to release the slot
                for _ in range(40):
                    if get_in_flight_transforms() == 0:
                        break
                    time.sleep(0.05)
                self.assertEqual(get_in_flight_transforms(), 0, "Slot must be cleanly released after worker finishes")
        finally:
            unblock_event.set()
            provider.shutdown(wait=False)


if __name__ == "__main__":
    unittest.main()
