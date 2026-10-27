"""
Tests for Local Text Repair (Spec 0004: Feature 30 Sandbox)
Validates Three-Tier Guard Protocol, Slot-Locker, SpanDiffEditor, Natural @N Edge Cases,
Filler-in-Meaning Preservation, FactGuard Veto, Fallbacks, Process Isolation,
Asynchronous Warmup, Cold-Start Safety, and Auto-Restart.
"""

import sys
import time
import unittest
import multiprocessing as mp
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.local_text_repair import (
    SlotLocker,
    SpanDiffEditor,
    LocalTextRepair,
    RepairStatus,
    RepairResult
)


def _controllable_worker_target(pipe):
    """Multi-command worker target for process isolation and restart tests."""
    pipe.send({"status": "ready"})
    while True:
        try:
            if not pipe.poll(timeout=0.1):
                continue
            req = pipe.recv()
            if not isinstance(req, dict):
                continue
            cmd = req.get("cmd")
            if cmd == "shutdown":
                break
            elif cmd == "infer":
                prompt = req.get("prompt", "")
                if "hang" in prompt:
                    time.sleep(10.0)  # Simulate hung native C++ thread
                else:
                    pipe.send({"status": "ok", "text": "We should"})
        except Exception:
            break


def _slow_startup_worker_target(pipe):
    """Simulates a model that takes 2 seconds to report ready."""
    time.sleep(2.0)
    pipe.send({"status": "ready"})


class TestLocalTextRepair(unittest.TestCase):

    def test_slot_locker_numbers_and_currency(self):
        text = "Please transfer $12,500 to account 589 by 2026-10-26."
        locked, slots = SlotLocker.lock(text)
        self.assertNotIn("$12,500", locked)
        self.assertNotIn("589", locked)
        self.assertIn("<SLOT_", locked)
        self.assertGreaterEqual(len(slots), 2)

        # Test exact restoration
        restored = SlotLocker.restore(locked, slots)
        self.assertEqual(restored, text)

    def test_slot_locker_critical_negations(self):
        text = "Do not deploy the patch, we cannot afford downtime and will never recover."
        locked, slots = SlotLocker.lock(text)
        self.assertNotIn("not", locked.lower().split())
        self.assertNotIn("cannot", locked.lower().split())
        self.assertNotIn("never", locked.lower().split())

        restored = SlotLocker.restore(locked, slots)
        self.assertEqual(restored, text)

    def test_slot_locker_code_identifiers(self):
        text = "Invoke getUserProfile and verify connection_string_db."
        locked, slots = SlotLocker.lock(text)
        self.assertNotIn("getUserProfile", locked)
        self.assertNotIn("connection_string_db", locked)

        restored = SlotLocker.restore(locked, slots)
        self.assertEqual(restored, text)

    def test_natural_at_n_and_literal_slot_preservation(self):
        """Verify natural @0, @1, @99, and <SLOT_0> tokens in user input never collide with compact slots."""
        raw = "um please ping @0 and @1 before 5 pm so check_user_handle does not overwrite <SLOT_0>"
        locked, slots = SlotLocker.lock(raw)
        self.assertIn("@0", slots.values())
        self.assertIn("@1", slots.values())
        self.assertIn("<SLOT_0>", slots.values())
        self.assertIn("check_user_handle", slots.values())

        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})
        repairer._llm = MagicMock(return_value={"choices": [{"text": "Please ping"}]})
        res = repairer.repair(raw)
        self.assertEqual(res.status, RepairStatus.REPAIRED)
        self.assertEqual(
            res.text,
            "Please ping @0 and @1 before 5 pm so check_user_handle does not overwrite <SLOT_0>."
        )
        repairer.shutdown()

    def test_natural_at_n_dropped_is_vetoed(self):
        """Verify that if natural @0 in the opening span is dropped by the SLM, Tier 3 vetoes it."""
        raw = "@0 and @1 must not accept port 8080 when allow_external_access is false in production"
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})
        # SLM drops @0 from the 2-word opening span '@0 and'
        repairer._llm = MagicMock(return_value={"choices": [{"text": "And"}]})
        res = repairer.repair(raw)
        self.assertEqual(res.status, RepairStatus.VETOED_FACT_MISMATCH)
        self.assertEqual(res.text, raw)
        self.assertIn("@0", res.veto_reason)
        repairer.shutdown()

    def test_filler_in_meaning_preserved_while_disfluency_removed(self):
        """Verify filler-in-meaning (subject, meta-mention, quoted, ER/Ah acronyms) are preserved."""
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})

        # Case 1: 'um' as grammatical subject at sentence start ('@0 is' 2-word opening span)
        raw1 = "um is a common filler word that should not break parse_token_stream in 2026"
        repairer._llm = MagicMock(return_value={"choices": [{"text": "@0 is"}]})
        res1 = repairer.repair(raw1)
        self.assertEqual(res1.status, RepairStatus.REPAIRED)
        self.assertEqual(
            res1.text,
            "Um is a common filler word that should not break parse_token_stream in 2026."
        )

        # Case 2: 'um' and 'uh' mentioned meta-linguistically after 'word' / 'token', while leading 'uh' is stripped
        raw2 = "uh please do not delete the word um or the token uh when testing filter_disfluencies"
        repairer._llm = MagicMock(return_value={"choices": [{"text": "Please do"}]})
        res2 = repairer.repair(raw2)
        self.assertEqual(res2.status, RepairStatus.REPAIRED)
        self.assertEqual(
            res2.text,
            "Please do not delete the word um or the token uh when testing filter_disfluencies."
        )

        # Case 3: Quoted 'um' and "uh" preserved while leading 'um' is stripped
        raw3 = 'um we should not strip \'um\' or "uh" from raw_transcript_buffer during 100 tests'
        repairer._llm = MagicMock(return_value={"choices": [{"text": "We should"}]})
        res3 = repairer.repair(raw3)
        self.assertEqual(res3.status, RepairStatus.REPAIRED)
        self.assertEqual(
            res3.text,
            'We should not strip \'um\' or "uh" from raw_transcript_buffer during 100 tests.'
        )

        # Case 4: Uppercase acronyms/units 'ER' and 'Ah' preserved while leading 'uh' and inline lowercase 'um' stripped
        raw4 = "uh the patient in ER room 4 must not wait um more than 15 minutes for a 50 Ah battery"
        repairer._llm = MagicMock(return_value={"choices": [{"text": "The patient"}]})
        res4 = repairer.repair(raw4)
        self.assertEqual(res4.status, RepairStatus.REPAIRED)
        self.assertEqual(
            res4.text,
            "The patient in ER room 4 must not wait more than 15 minutes for a 50 Ah battery."
        )
        repairer.shutdown()

    def test_interrogative_question_mark_restoration(self):
        """Verify interrogative openings receive '?' terminal punctuation in SpanDiffEditor."""
        raw = "um why did check_status_code return 404 instead of 200 when retry_limit_enabled was not set"
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})
        repairer._llm = MagicMock(return_value={"choices": [{"text": "Why did"}]})
        res = repairer.repair(raw)
        self.assertEqual(res.status, RepairStatus.REPAIRED)
        self.assertEqual(
            res.text,
            "Why did check_status_code return 404 instead of 200 when retry_limit_enabled was not set?"
        )
        repairer.shutdown()

    def test_span_diff_editor_windowed_repair(self):
        """Verify SpanDiffEditor extracts opening span, bounds max_tokens dynamically, and splices cleanly."""
        raw = "um we must not deploy commit 100 to production before 1 pm because check_status_code returned 400"
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})

        mock_llm = MagicMock()
        mock_llm.return_value = {"choices": [{"text": "We must"}]}
        repairer._llm = mock_llm

        res = repairer.repair(raw)
        self.assertEqual(res.status, RepairStatus.REPAIRED)
        self.assertEqual(
            res.text,
            "We must not deploy commit 100 to production before 1 pm because check_status_code returned 400."
        )
        # Ensure max_tokens was dynamically bounded for 'um we must' -> 2 content words + 1 = 3 tokens
        _, kwargs = mock_llm.call_args
        self.assertEqual(kwargs.get("max_tokens"), 3)
        repairer.shutdown()

    def test_disabled_engine_returns_unprovisioned_fallback(self):
        repairer = LocalTextRepair(config={"local_text_repair_enabled": False})
        res = repairer.repair("Hello world this is a test")
        self.assertEqual(res.status, RepairStatus.FALLBACK_UNPROVISIONED)
        self.assertEqual(res.text, "Hello world this is a test")
        self.assertTrue(res.fallback_used)
        self.assertLess(res.latency_ms, 15.0)

    def test_empty_or_whitespace_transcript_returns_unchanged(self):
        """Empty or whitespace input must bypass SLM infilling and return immediately."""
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})
        res_empty = repairer.repair("")
        self.assertEqual(res_empty.status, RepairStatus.REPAIRED)
        self.assertEqual(res_empty.text, "")
        self.assertEqual(res_empty.latency_ms, 0.0)

        res_space = repairer.repair("   \n\t  ")
        self.assertEqual(res_space.status, RepairStatus.REPAIRED)
        self.assertEqual(res_space.text, "   \n\t  ")

    def test_unprovisioned_model_falls_back_safely(self):
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": None})
        res = repairer.repair("Test transcription without model path")
        self.assertEqual(res.status, RepairStatus.FALLBACK_UNPROVISIONED)
        self.assertEqual(res.text, "Test transcription without model path")
        self.assertTrue(res.fallback_used)

    def test_model_load_failure_during_init_falls_back_safely(self):
        """Simulate worker process startup failure or corrupt model."""
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "corrupt.gguf"})
        with patch.object(repairer, "_ensure_worker_process", return_value=False):
            res = repairer.repair("Test import error fallback")
            self.assertEqual(res.status, RepairStatus.FALLBACK_UNPROVISIONED)
            self.assertEqual(res.text, "Test import error fallback")
            self.assertTrue(res.fallback_used)

    def test_tier3_factguard_vetoes_dropped_negation(self):
        """Simulate an SLM that drops a negation: FactGuard must VETO and return raw input."""
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})

        raw = "Do not delete the production database."

        mock_llm = MagicMock()
        mock_llm.return_value = {
            "choices": [{"text": "Do delete the production database."}]
        }
        repairer._llm = mock_llm

        res = repairer.repair(raw)
        self.assertEqual(res.status, RepairStatus.VETOED_FACT_MISMATCH)
        self.assertEqual(res.text, raw) # Must fall back to raw input containing 'not'
        self.assertTrue(res.fallback_used)
        self.assertIn("FactGuard veto", res.veto_reason)
        repairer.shutdown()

    def test_tier3_factguard_vetoes_dropped_code_identifier_slot(self):
        """Simulate an SLM that drops a locked code-identifier slot (<SLOT_0>): Tier 3 must VETO."""
        repairer = LocalTextRepair(config={
            "local_text_repair_enabled": True,
            "local_text_repair_model_path": "mock.gguf",
            "local_text_repair_span_diff": False,
        })

        raw = "um please invoke getUserProfile and verify connection_string_db"

        mock_llm = MagicMock()
        # Drops <SLOT_1> (connection_string_db) and hallucinates <SLOT_99>
        mock_llm.return_value = {
            "choices": [{"text": "Please invoke <SLOT_0> and verify <SLOT_99>."}]
        }
        repairer._llm = mock_llm

        res = repairer.repair(raw)
        self.assertEqual(res.status, RepairStatus.VETOED_FACT_MISMATCH)
        self.assertEqual(res.text, raw)
        self.assertTrue(res.fallback_used)
        self.assertIn("connection_string_db", res.veto_reason)
        self.assertIn("<SLOT_99>", res.veto_reason)
        repairer.shutdown()

    def test_tier3_factguard_approves_safe_cleaned_text(self):
        """Simulate an SLM that cleans punctuation while preserving slots."""
        repairer = LocalTextRepair(config={
            "local_text_repair_enabled": True,
            "local_text_repair_model_path": "mock.gguf",
            "local_text_repair_span_diff": False,
        })

        raw = "we should like deploy <SLOT_0> to cluster <SLOT_1>"

        mock_llm = MagicMock()
        mock_llm.return_value = {
            "choices": [{"text": "We should deploy <SLOT_0> to cluster <SLOT_1>."}]
        }
        repairer._llm = mock_llm

        res = repairer.repair("we should like deploy not to cluster 42")
        self.assertEqual(res.status, RepairStatus.REPAIRED)
        self.assertFalse(res.fallback_used)
        self.assertIn("not", res.text)
        self.assertIn("42", res.text)
        repairer.shutdown()

    def test_malformed_llm_output_falls_back_safely(self):
        """Simulate an SLM returning malformed structure or raising an exception."""
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})

        mock_broken = MagicMock(return_value={"error": "syntax"})
        repairer._llm = mock_broken
        res1 = repairer.repair("Testing malformed LLM response")
        self.assertEqual(res1.status, RepairStatus.FALLBACK_ERROR)
        self.assertEqual(res1.text, "Testing malformed LLM response")
        self.assertTrue(res1.fallback_used)

        mock_throwing = MagicMock(side_effect=RuntimeError("DirectML out of memory"))
        repairer._llm = mock_throwing
        res2 = repairer.repair("Testing runtime exception handling")
        self.assertEqual(res2.status, RepairStatus.FALLBACK_ERROR)
        self.assertEqual(res2.text, "Testing runtime exception handling")
        self.assertTrue(res2.fallback_used)
        repairer.shutdown()

    def test_timeout_falls_back_to_raw_transcript(self):
        """Simulate inference exceeding the 400ms deadline in mock/thread mode."""
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})
        repairer.MAX_LATENCY_MS = 15.0

        def slow_llm(*args, **kwargs):
            time.sleep(0.035)
            return {"choices": [{"text": "Slow response"}]}

        repairer._llm = slow_llm
        res = repairer.repair("Test timeout handling in local repair engine")
        self.assertEqual(res.status, RepairStatus.FALLBACK_TIMEOUT)
        self.assertEqual(res.text, "Test timeout handling in local repair engine")
        self.assertTrue(res.fallback_used)
        repairer.shutdown()

    def test_async_worker_aborts_without_blocking_caller(self):
        """Verify that an extremely slow worker (e.g. 1s) does NOT block caller beyond deadline."""
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})
        repairer.MAX_LATENCY_MS = 25.0

        def hanging_llm(*args, **kwargs):
            time.sleep(1.0)
            return {"choices": [{"text": "Late"}]}

        repairer._llm = hanging_llm
        t0 = time.perf_counter()
        res = repairer.repair("Test non-blocking timeout abort")
        caller_duration_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(res.status, RepairStatus.FALLBACK_TIMEOUT)
        self.assertEqual(res.text, "Test non-blocking timeout abort")
        self.assertLess(caller_duration_ms, 150.0)
        repairer.shutdown(wait=False)

    def test_process_worker_hard_termination_on_timeout(self):
        """Verify that a hanging process worker is forcibly terminated at OS level on timeout."""
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})
        repairer.MAX_LATENCY_MS = 30.0

        ctx = mp.get_context("spawn")
        p_conn, c_conn = ctx.Pipe(duplex=True)
        worker = ctx.Process(target=_controllable_worker_target, args=(c_conn,), daemon=True)
        worker.start()
        self.assertTrue(worker.is_alive())

        repairer._worker_process = worker
        repairer._parent_pipe = p_conn
        repairer._is_ready = True

        t0 = time.perf_counter()
        res = repairer.repair("Test process worker hang timeout")
        caller_duration_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(res.status, RepairStatus.FALLBACK_TIMEOUT)
        self.assertEqual(res.text, "Test process worker hang timeout")
        self.assertTrue(res.fallback_used)
        self.assertLess(caller_duration_ms, 150.0)

        # Confirm OS-level termination
        self.assertFalse(worker.is_alive())
        self.assertIsNone(repairer._worker_process)
        repairer.shutdown()

    def test_cold_start_fallback_when_worker_unready(self):
        """Verify that if worker is unready/cold, repair() immediately falls back without blocking."""
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})
        repairer.MAX_LATENCY_MS = 25.0

        # Start a slow-starting worker that takes 2.0s
        ctx = mp.get_context("spawn")
        p_conn, c_conn = ctx.Pipe(duplex=True)
        worker = ctx.Process(target=_slow_startup_worker_target, args=(c_conn,), daemon=True)
        worker.start()

        repairer._worker_process = worker
        repairer._parent_pipe = p_conn
        repairer._is_ready = False  # Not yet ready!

        t0 = time.perf_counter()
        res = repairer.repair("Test cold start fast fallback")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(res.status, RepairStatus.FALLBACK_UNPROVISIONED)
        self.assertEqual(res.text, "Test cold start fast fallback")
        self.assertTrue(res.fallback_used)
        self.assertLess(elapsed_ms, 100.0, f"Cold start check blocked for {elapsed_ms} ms, expected < 100 ms")

        # Cleanup
        worker.terminate()
        worker.join(0.2)
        repairer.shutdown()

    def test_worker_auto_restart_after_hard_termination(self):
        """Verify that after a process worker is killed on timeout, a fresh worker is respawned."""
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})
        repairer.MAX_LATENCY_MS = 30.0

        ctx = mp.get_context("spawn")

        # 1. First worker (hangs and gets killed)
        p1, c1 = ctx.Pipe(duplex=True)
        w1 = ctx.Process(target=_controllable_worker_target, args=(c1,), daemon=True)
        w1.start()
        repairer._worker_process = w1
        repairer._parent_pipe = p1
        repairer._is_ready = True

        res1 = repairer.repair("First call hang")
        self.assertEqual(res1.status, RepairStatus.FALLBACK_TIMEOUT)
        self.assertFalse(w1.is_alive())
        self.assertIsNone(repairer._worker_process)

        # 2. Simulate second worker spawned by self-healing
        p2, c2 = ctx.Pipe(duplex=True)
        w2 = ctx.Process(target=_controllable_worker_target, args=(c2,), daemon=True)
        w2.start()
        self.assertTrue(p2.poll(timeout=2.0))
        ready_msg = p2.recv()
        self.assertEqual(ready_msg.get("status"), "ready")

        repairer._worker_process = w2
        repairer._parent_pipe = p2
        repairer._is_ready = True

        repairer.MAX_LATENCY_MS = 400.0
        res2 = repairer.repair("we should deploy not to cluster 42")
        self.assertEqual(res2.status, RepairStatus.REPAIRED)
        self.assertFalse(res2.fallback_used)
        self.assertIn("not", res2.text)
        self.assertIn("42", res2.text)

        w2.terminate()
        w2.join(0.2)
        repairer.shutdown()

    def test_warmup_async_preloads_in_background(self):
        """Verify that warmup_async() returns an immediate future and executes non-blocking."""
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})

        # Mock warmup to take 50ms on background thread
        def mock_warmup():
            time.sleep(0.05)
            return True

        with patch.object(repairer, "warmup", side_effect=mock_warmup):
            t0 = time.perf_counter()
            future = repairer.warmup_async()
            init_elapsed_ms = (time.perf_counter() - t0) * 1000.0

            # Must return immediately without waiting for warmup
            self.assertLess(init_elapsed_ms, 25.0)
            self.assertTrue(repairer._warmup_in_progress)

            # Await future
            res = future.result(timeout=1.0)
            self.assertTrue(res)
            self.assertFalse(repairer._warmup_in_progress)
            self.assertTrue(repairer._is_ready)

        repairer.shutdown()

    def test_orchestrator_initializes_and_warms_up_repairer(self):
        """Verify that FlowOrchestrator automatically initializes and calls warmup_async on text_repair."""
        from engine.orchestrator import FlowOrchestrator

        with patch("engine.orchestrator.load_config", return_value={"local_text_repair_enabled": True, "audio_input_selection": {"mode": "default"}}), \
             patch("engine.orchestrator.resolve_audio_input"), \
             patch("engine.orchestrator.AudioRecorder"), \
             patch("engine.orchestrator.STTEngine"), \
             patch("engine.orchestrator.ContextProcessor"), \
             patch("engine.orchestrator.AudioDucker"), \
             patch("engine.orchestrator.AudioFeedback"), \
             patch("engine.orchestrator.get_hotkey_service"), \
             patch.object(LocalTextRepair, "warmup_async") as mock_warmup:
            orch = FlowOrchestrator()
            self.assertIsNotNone(orch.text_repair)
            self.assertTrue(mock_warmup.called)

            with patch.object(orch.text_repair, "shutdown") as mock_shutdown:
                orch.stop()
                self.assertTrue(mock_shutdown.called)


if __name__ == "__main__":
    unittest.main()
