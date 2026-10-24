"""
Tests for Feature 29: Benchmark Visible Delivery Observer & Latency Contracts
Covers:
- Precision stop-action to visible text delta observation
- Baseline isolation (pre-existing text is not counted as new delivery)
- Decoupling of delivery observation from transcription accuracy
- Truthful None latency for unreadable buffers or timeouts
- Incremental text settlement tracking
- Aggregate delivery summary metrics
"""

import os
import sys
import time
import unittest
import logging
import threading

logger = logging.getLogger("FlowPilot.TestDeliveryObserver")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from benchmarks.delivery_observer import (
    DeliveryObserver,
    ObservedDeliveryStatus,
    DeliveryObservationRecord,
    summarize_observed_deliveries
)


class TestDeliveryObserver(unittest.TestCase):

    def test_observer_measures_first_and_settled_appearance(self):
        """
        Calibrated simulation: Text appears 40ms after stop action and settles 30ms later.
        Observer must record both first visible timestamp and settled timestamp accurately.
        """
        buffer_state = ["Initial content\n"]

        def reader():
            return buffer_state[0]

        observer = DeliveryObserver(trial_id="trial-001", target_app="notepad")
        t_stop = time.perf_counter()
        observer.capture_baseline(reader)

        # Background simulated delivery: text appends after 40ms
        def simulate_paste():
            time.sleep(0.04)
            buffer_state[0] = "Initial content\nNewly injected text"

        import threading
        t = threading.Thread(target=simulate_paste)
        t.start()

        record = observer.observe_delivery(
            stop_timestamp=t_stop,
            buffer_reader=reader,
            timeout_sec=1.0,
            settle_window_sec=0.05,
            poll_interval_sec=0.005
        )
        t.join()

        self.assertEqual(record.status, ObservedDeliveryStatus.VERIFIED_FIRST_DELIVERY)
        self.assertIsNotNone(record.stop_to_first_visible_ms)
        self.assertIsNotNone(record.stop_to_settled_visible_ms)
        self.assertGreaterEqual(record.stop_to_first_visible_ms, 35.0)
        self.assertGreaterEqual(record.stop_to_settled_visible_ms, record.stop_to_first_visible_ms)
        self.assertEqual(record.observed_text_delta, "Newly injected text")

    def test_preexisting_identical_text_not_counted_as_delivery(self):
        """
        If target already contained the exact text before dictation,
        and no new text was injected, observer reports TIMEOUT, NOT 0.0ms latency.
        """
        buffer_state = ["Already present phrase"]

        def reader():
            return buffer_state[0]

        observer = DeliveryObserver(trial_id="trial-002")
        t_stop = time.perf_counter()
        observer.capture_baseline(reader)

        # No text changes occur
        record = observer.observe_delivery(
            stop_timestamp=t_stop,
            buffer_reader=reader,
            timeout_sec=0.08,
            poll_interval_sec=0.005
        )

        self.assertEqual(record.status, ObservedDeliveryStatus.TIMEOUT)
        self.assertIsNone(record.stop_to_first_visible_ms)
        self.assertIsNone(record.stop_to_settled_visible_ms)
        self.assertEqual(record.observed_text_delta, "")

    def test_wrong_transcription_is_valid_delivery(self):
        """
        Delivery observation is decoupled from transcription accuracy:
        If model transcribes 'wrong words' instead of reference, and 'wrong words'
        appears in the target document, delivery is VERIFIED_FIRST_DELIVERY.
        """
        buffer_state = [""]

        def reader():
            return buffer_state[0]

        observer = DeliveryObserver(trial_id="trial-003")
        t_stop = time.perf_counter()
        observer.capture_baseline(reader)

        buffer_state[0] = "wrong transcribed text"

        record = observer.observe_delivery(
            stop_timestamp=t_stop,
            buffer_reader=reader,
            timeout_sec=0.5,
            settle_window_sec=0.02,
            poll_interval_sec=0.005
        )

        self.assertEqual(record.status, ObservedDeliveryStatus.VERIFIED_FIRST_DELIVERY)
        self.assertEqual(record.observed_text_delta, "wrong transcribed text")
        self.assertIsNotNone(record.stop_to_first_visible_ms)

    def test_deletion_not_counted_as_delivery(self):
        """
        User pressing Backspace or deleting characters shortens buffer.
        Shortened buffer MUST NOT be counted as a delivery.
        """
        buffer_state = ["Original long text in document"]

        def reader():
            return buffer_state[0]

        observer = DeliveryObserver(trial_id="trial-del")
        t_stop = time.perf_counter()
        observer.capture_baseline(reader)

        # Buffer is shortened (deletion)
        buffer_state[0] = "Original"

        record = observer.observe_delivery(
            stop_timestamp=t_stop,
            buffer_reader=reader,
            timeout_sec=0.10,
            settle_window_sec=0.03,
            poll_interval_sec=0.005
        )

        self.assertEqual(record.status, ObservedDeliveryStatus.TIMEOUT)
        self.assertIsNone(record.stop_to_first_visible_ms)

    def test_unrelated_text_change_rejected_when_injected_text_known(self):
        """
        If injected_text is specified, an unrelated document edit (e.g. clock ticker or stray key)
        cannot establish delivery or prove a different target identity.
        """
        buffer_state = ["Doc start: "]

        def reader():
            return buffer_state[0]

        observer = DeliveryObserver(trial_id="trial-unrelated")
        t_stop = time.perf_counter()
        observer.capture_baseline(reader)

        # Unrelated text appears
        buffer_state[0] = "Doc start: [12:00:01 Ticker Update]"

        record = observer.observe_delivery(
            stop_timestamp=t_stop,
            buffer_reader=reader,
            injected_text="def my_function():",
            timeout_sec=0.20,
            settle_window_sec=0.03,
            poll_interval_sec=0.005
        )

        self.assertEqual(record.status, ObservedDeliveryStatus.TIMEOUT)
        self.assertIn("correlated", record.missing_data_reason)

    def test_unreadable_target_returns_unverified_dispatch_with_none_latency(self):
        """
        When target buffer cannot be read (e.g. elevated or console app),
        observer reports UNVERIFIED_DISPATCH and keeps latency as None.
        """
        def unreadable_reader():
            return None

        observer = DeliveryObserver(trial_id="trial-004")
        t_stop = time.perf_counter()

        record = observer.observe_delivery(
            stop_timestamp=t_stop,
            buffer_reader=unreadable_reader,
            timeout_sec=0.1
        )

        self.assertEqual(record.status, ObservedDeliveryStatus.UNVERIFIED_DISPATCH)
        self.assertIsNone(record.stop_to_first_visible_ms)
        self.assertIn("unreadable", record.missing_data_reason.lower())

    def test_incremental_output_settlement(self):
        """
        Incremental streaming/typing chunks are tracked:
        First change timestamp records the first chunk, settled timestamp records final chunk.
        """
        buffer_state = [""]

        def reader():
            return buffer_state[0]

        observer = DeliveryObserver(trial_id="trial-005")
        t_stop = time.perf_counter()
        observer.capture_baseline(reader)

        def stream_chunks():
            time.sleep(0.02)
            buffer_state[0] = "Part 1 "
            time.sleep(0.03)
            buffer_state[0] = "Part 1 Part 2"

        import threading
        t = threading.Thread(target=stream_chunks)
        t.start()

        record = observer.observe_delivery(
            stop_timestamp=t_stop,
            buffer_reader=reader,
            timeout_sec=1.0,
            settle_window_sec=0.05,
            poll_interval_sec=0.005
        )
        t.join()

        self.assertEqual(record.status, ObservedDeliveryStatus.VERIFIED_FIRST_DELIVERY)
        self.assertEqual(record.observed_text_delta, "Part 1 Part 2")
        self.assertGreater(record.stop_to_settled_visible_ms, record.stop_to_first_visible_ms)

    def observe_fixture(self, baseline, current, payload=None, timeout=0.06):
        observer = DeliveryObserver("fixture")
        observer.capture_baseline(lambda: baseline)
        return observer.observe_delivery(time.perf_counter(), lambda: current,
            injected_text=payload, timeout_sec=timeout, settle_window_sec=0.01,
            poll_interval_sec=0.002)

    def test_unreadable_baseline_cannot_become_empty_baseline(self):
        for bad_reader in (lambda: None, lambda: (_ for _ in ()).throw(RuntimeError("read failed"))):
            observer = DeliveryObserver("baseline")
            observer.capture_baseline(bad_reader)
            record = observer.observe_delivery(time.perf_counter(), lambda: "old text",
                timeout_sec=0.04)
            self.assertEqual(record.status, ObservedDeliveryStatus.UNVERIFIED_DISPATCH)
            self.assertIsNone(record.stop_to_first_visible_ms)

    def test_mid_document_insertion_excludes_preexisting_payload(self):
        record = self.observe_fixture("hello TOKEN end", "hello unrelated TOKEN end", "TOKEN")
        self.assertEqual(record.status, ObservedDeliveryStatus.TIMEOUT)
        self.assertIsNone(record.stop_to_first_visible_ms)
        record = self.observe_fixture("before after", "before TOKENafter", "TOKEN")
        self.assertEqual(record.status, ObservedDeliveryStatus.VERIFIED_FIRST_DELIVERY)
        self.assertEqual(record.observed_text_delta, "TOKEN")

    def test_duplicate_and_partial_payloads_are_not_verified(self):
        for text, expected in (("wordword", ObservedDeliveryStatus.DUPLICATE_DELIVERY),
                               ("word word", ObservedDeliveryStatus.DUPLICATE_DELIVERY),
                               ("wo", ObservedDeliveryStatus.PARTIAL_DELIVERY)):
            record = self.observe_fixture("", text, "word")
            self.assertEqual(record.status, expected)
            self.assertEqual(record.observed_text_delta, text)
            self.assertIsNotNone(record.stop_to_first_visible_ms)
            summary = summarize_observed_deliveries([record])
            self.assertEqual(summary["verified_count"], 0)

    def test_return_to_baseline_restarts_settlement(self):
        observer = DeliveryObserver("reset")
        observer.capture_baseline(lambda: "")
        start = time.perf_counter()
        def reader():
            elapsed = time.perf_counter() - start
            return "text" if elapsed < 0.015 or elapsed >= 0.045 else ""
        record = observer.observe_delivery(start, reader, injected_text="text",
            timeout_sec=0.15, settle_window_sec=0.03, poll_interval_sec=0.002)
        self.assertEqual(record.status, ObservedDeliveryStatus.VERIFIED_FIRST_DELIVERY)
        self.assertGreaterEqual(time.perf_counter() - start, 0.075)
        self.assertGreaterEqual(record.stop_to_settled_visible_ms, 45)
        self.assertGreaterEqual(record.stop_to_first_visible_ms, 45)

    def test_return_to_baseline_is_not_partial_delivery(self):
        observer = DeliveryObserver("removed")
        observer.capture_baseline(lambda: "")
        start = time.perf_counter()
        record = observer.observe_delivery(start,
            lambda: "text" if time.perf_counter() - start < 0.01 else "",
            injected_text="text", timeout_sec=0.05, settle_window_sec=0.03,
            poll_interval_sec=0.002)
        self.assertEqual(record.status, ObservedDeliveryStatus.TIMEOUT)
        self.assertIsNone(record.stop_to_first_visible_ms)

    def test_stalled_reads_are_bounded_and_do_not_spawn_unbounded_workers(self):
        release = threading.Event()
        entered = []
        def blocked():
            entered.append(1)
            release.wait()
            return "text"
        try:
            start = time.perf_counter()
            for index in range(8):
                observer = DeliveryObserver(str(index))
                observer.capture_baseline(lambda: "")
                record = observer.observe_delivery(time.perf_counter(), blocked, timeout_sec=0.02)
                self.assertEqual(record.status, ObservedDeliveryStatus.UNVERIFIED_DISPATCH)
                self.assertIsNone(record.stop_to_first_visible_ms)
            self.assertLess(time.perf_counter() - start, 0.5)
            self.assertLessEqual(len(entered), 4)
        finally:
            release.set()
            # Allow only our daemon reads to release their process wide slots.
            deadline = time.perf_counter() + 0.5
            while any(t.name == "FlowPilot.BenchmarkRead" for t in threading.enumerate()) and time.perf_counter() < deadline:
                time.sleep(0.001)

    def test_baseline_read_and_elapsed_stop_deadline_are_bounded(self):
        release = threading.Event()
        observer = DeliveryObserver("bounded-baseline")
        try:
            start = time.perf_counter()
            observer.capture_baseline(lambda: release.wait(), timeout_sec=0.02)
            self.assertLess(time.perf_counter() - start, 0.3)
            self.assertFalse(observer.baseline_captured)
        finally:
            release.set()
        observer = DeliveryObserver("expired")
        observer.capture_baseline(lambda: "")
        calls = []
        record = observer.observe_delivery(time.perf_counter() - 1,
            lambda: calls.append(1), timeout_sec=0.02)
        self.assertEqual(calls, [])
        self.assertEqual(record.status, ObservedDeliveryStatus.TIMEOUT)

    def test_reader_failure_after_insertion_clears_unverified_timing(self):
        observer = DeliveryObserver("lost-reader")
        observer.capture_baseline(lambda: "")
        reads = iter(["text", None])
        record = observer.observe_delivery(time.perf_counter(), lambda: next(reads),
            injected_text="text", timeout_sec=0.06, settle_window_sec=0.03)
        self.assertEqual(record.status, ObservedDeliveryStatus.UNVERIFIED_DISPATCH)
        self.assertIsNone(record.first_observed_timestamp)
        self.assertIsNone(record.stop_to_first_visible_ms)
        self.assertIsNone(record.stop_to_settled_visible_ms)

    def test_singleton_percentiles_preserve_sample(self):
        record = DeliveryObservationRecord("one", "fixture", None, "", 0,
            stop_to_first_visible_ms=123.4, stop_to_settled_visible_ms=156.7,
            status=ObservedDeliveryStatus.VERIFIED_FIRST_DELIVERY)
        summary = summarize_observed_deliveries([record])
        self.assertEqual(summary["first_visible_p50_ms"], 123.4)
        self.assertEqual(summary["first_visible_p95_ms"], 123.4)
        self.assertEqual(summary["settled_visible_p95_ms"], 156.7)

    def test_summarize_observed_deliveries_metrics(self):
        """
        summarize_observed_deliveries calculates p50/p95 exclusively from verified deliveries,
        preserving failure counts and unverified denominators.
        """
        records = [
            DeliveryObservationRecord(
                trial_id="t1", target_app="notepad", target_hwnd=1, baseline_text="",
                stop_action_timestamp=100.0, stop_to_first_visible_ms=80.0, stop_to_settled_visible_ms=120.0,
                status=ObservedDeliveryStatus.VERIFIED_FIRST_DELIVERY
            ),
            DeliveryObservationRecord(
                trial_id="t2", target_app="notepad", target_hwnd=1, baseline_text="",
                stop_action_timestamp=101.0, stop_to_first_visible_ms=120.0, stop_to_settled_visible_ms=160.0,
                status=ObservedDeliveryStatus.VERIFIED_FIRST_DELIVERY
            ),
            DeliveryObservationRecord(
                trial_id="t3", target_app="cmd.exe", target_hwnd=2, baseline_text="",
                stop_action_timestamp=102.0, status=ObservedDeliveryStatus.UNVERIFIED_DISPATCH
            ),
            DeliveryObservationRecord(
                trial_id="t4", target_app="notepad", target_hwnd=1, baseline_text="",
                stop_action_timestamp=103.0, status=ObservedDeliveryStatus.TIMEOUT
            ),
        ]

        summary = summarize_observed_deliveries(records)
        self.assertEqual(summary["total_trials"], 4)
        self.assertEqual(summary["verified_count"], 2)
        self.assertEqual(summary["unverified_count"], 1)
        self.assertEqual(summary["timeout_count"], 1)
        self.assertEqual(summary["verified_first_delivery_rate"], 0.50)
        self.assertIsNotNone(summary["first_visible_p50_ms"])
        self.assertIsNotNone(summary["settled_visible_p50_ms"])


if __name__ == "__main__":
    unittest.main()
