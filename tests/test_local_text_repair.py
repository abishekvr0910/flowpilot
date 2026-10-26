"""
Tests for Local Text Repair (Spec 0004: Feature 30 Sandbox)
Validates Three-Tier Guard Protocol, Slot-Locker, FactGuard Veto, and Fallbacks.
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
    LocalTextRepair,
    RepairStatus,
    RepairResult
)


def _hanging_worker_target(pipe):
    """Helper target for testing process-level worker termination."""
    pipe.send({"status": "ready"})
    while True:
        try:
            if pipe.poll(timeout=0.1):
                pipe.recv()
                time.sleep(10.0)  # Simulate hung C++ native thread
        except Exception:
            break


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
        """Simulate llama-cpp import or initialization exception."""
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

        # Mock LLM output that stripped the negation slot
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

    def test_tier3_factguard_approves_safe_cleaned_text(self):
        """Simulate an SLM that cleans punctuation while preserving slots."""
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})

        raw = "we should like deploy <SLOT_0> to cluster <SLOT_1>"

        # Mock LLM that cleans up and keeps slots
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

        # 1. Output missing 'choices' key
        mock_broken = MagicMock(return_value={"error": "syntax"})
        repairer._llm = mock_broken
        res1 = repairer.repair("Testing malformed LLM response")
        self.assertEqual(res1.status, RepairStatus.FALLBACK_ERROR)
        self.assertEqual(res1.text, "Testing malformed LLM response")
        self.assertTrue(res1.fallback_used)

        # 2. LLM raising runtime exception
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
        repairer.MAX_LATENCY_MS = 15.0 # Strict 15ms deadline for test

        def slow_llm(*args, **kwargs):
            time.sleep(0.035) # 35ms > 15ms
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
        self.assertLess(caller_duration_ms, 150.0, f"Caller was blocked for {caller_duration_ms} ms, expected < 150 ms")
        repairer.shutdown(wait=False)

    def test_process_worker_hard_termination_on_timeout(self):
        """Verify that a hanging process worker is forcibly terminated at OS level on timeout."""
        repairer = LocalTextRepair(config={"local_text_repair_enabled": True, "local_text_repair_model_path": "mock.gguf"})
        repairer.MAX_LATENCY_MS = 30.0

        ctx = mp.get_context("spawn")
        p_conn, c_conn = ctx.Pipe(duplex=True)
        worker = ctx.Process(target=_hanging_worker_target, args=(c_conn,), daemon=True)
        worker.start()
        self.assertTrue(worker.is_alive())

        # Wire running worker into repairer
        repairer._worker_process = worker
        repairer._parent_pipe = p_conn

        t0 = time.perf_counter()
        res = repairer.repair("Test process worker timeout termination")
        caller_duration_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(res.status, RepairStatus.FALLBACK_TIMEOUT)
        self.assertEqual(res.text, "Test process worker timeout termination")
        self.assertTrue(res.fallback_used)
        self.assertLess(caller_duration_ms, 150.0)

        # Confirm OS-level termination happened
        self.assertFalse(worker.is_alive())
        self.assertIsNone(repairer._worker_process)
        repairer.shutdown()


if __name__ == "__main__":
    unittest.main()
