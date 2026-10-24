"""
FlowPilot Benchmark Visible Delivery Observer (Feature 29: Competitive Validation)
High-precision monotonic observation of actual visible document appearance.

Measures:
- Stop action to first visible text change in target document (T_stop -> T_first_visible)
- Stop action to settled visible text (T_stop -> T_settled)
- Injection dispatch to visible appearance (T_dispatch -> T_first_visible)

Guarantees:
- Decouples text delivery timing from transcription accuracy (wrong transcription delivered is valid delivery)
- Never substitutes internal pipeline dispatch for visible delivery
- Preserves None latency for unreadable targets, timeouts, or safe refusals
- Baseline-aware: ignores pre-existing text in the target document
"""

import time
import logging
import threading
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any, List

logger = logging.getLogger("FlowPilot.DeliveryObserver")


# Slots are retained until a callback actually returns, even after its caller times out.
# Daemon threads cannot hold up interpreter exit; a stalled adapter is never retried
# with an unbounded queue or an unbounded collection of abandoned workers.
_READ_SLOTS = threading.BoundedSemaphore(4)


def _read_before(reader, deadline):
    remaining = deadline - time.perf_counter()
    if remaining <= 0 or not _READ_SLOTS.acquire(blocking=False):
        return None
    done = threading.Event()
    result = [None]

    def run():
        try:
            value = reader()
            if isinstance(value, str):
                result[0] = value
        except Exception:
            logger.debug("Benchmark document reader failed", exc_info=True)
        finally:
            _READ_SLOTS.release()
            done.set()

    worker = threading.Thread(target=run, name="FlowPilot.BenchmarkRead", daemon=True)
    try:
        worker.start()
    except Exception:
        _READ_SLOTS.release()
        return None
    done.wait(max(0.0, deadline - time.perf_counter()))
    return result[0] if done.is_set() and time.perf_counter() <= deadline else None


def _insertion_delta(baseline, current):
    """Return only a pure insertion, excluding all existing prefix and suffix text."""
    added = len(current) - len(baseline)
    if added <= 0:
        return ""
    prefix = 0
    while prefix < len(baseline) and baseline[prefix] == current[prefix]:
        prefix += 1
    if current[prefix + added:] != baseline[prefix:]:
        return ""
    return current[prefix:prefix + added]


def _is_duplicate_injection(delta: str, injected_text: Optional[str]) -> bool:
    """Detect whether delta contains repeated/duplicated injection of expected text."""
    if not delta or not injected_text:
        return False
    d = delta.strip()
    exp = injected_text.strip()
    if not exp or d == exp:
        return False
    # Exact contiguous repetition: e.g. "phrasephrase"
    if len(d) > len(exp) and d == exp * (len(d) // len(exp)):
        return True
    # Word/token sequence repetition: e.g. "phrase phrase", "hello world hello world"
    words_exp = exp.split()
    words_d = d.split()
    if words_exp and len(words_d) >= 2 * len(words_exp):
        n = len(words_d) // len(words_exp)
        if words_d == words_exp * n:
            return True
    return False


class ObservedDeliveryStatus(str, Enum):
    """Authoritative states for target document delivery observation."""
    VERIFIED_FIRST_DELIVERY = "VERIFIED_FIRST_DELIVERY"  # Delivered on initial attempt into verified target
    UNVERIFIED_DISPATCH = "UNVERIFIED_DISPATCH"          # Keystroke dispatched, target buffer unreadable
    SAFE_REFUSAL = "SAFE_REFUSAL"                        # Target lost or guarded; aborted without dispatch
    PARTIAL_DELIVERY = "PARTIAL_DELIVERY"                # Text appeared but was truncated before settlement
    WRONG_TARGET = "WRONG_TARGET"                        # Focus shifted; text delivered into wrong window
    DUPLICATE_DELIVERY = "DUPLICATE_DELIVERY"            # Repeated insertion detected
    RECOVERED_DELIVERY = "RECOVERED_DELIVERY"            # Initial paste failed; explicit user recovery succeeded
    CANCELLED = "CANCELLED"                              # Dictation session cancelled before injection
    TIMEOUT = "TIMEOUT"                                  # No text change detected within observation deadline


@dataclass
class DeliveryObservationRecord:
    trial_id: str
    target_app: str
    target_hwnd: Optional[int]
    baseline_text: str
    stop_action_timestamp: float
    dispatch_timestamp: Optional[float] = None
    first_observed_timestamp: Optional[float] = None
    settled_observed_timestamp: Optional[float] = None
    stop_to_first_visible_ms: Optional[float] = None
    stop_to_settled_visible_ms: Optional[float] = None
    status: ObservedDeliveryStatus = ObservedDeliveryStatus.TIMEOUT
    observed_text_delta: str = ""
    missing_data_reason: Optional[str] = None
    observation_method: str = "custom_reader"


class DeliveryObserver:
    """
    Independent benchmark observer that polls a target document buffer reader
    to capture the precise millisecond when newly dictated text appears.
    """

    def __init__(self, trial_id: str, target_app: str = "notepad", target_hwnd: Optional[int] = None):
        self.trial_id = trial_id
        self.target_app = target_app
        self.target_hwnd = target_hwnd
        self.baseline_text: str = ""
        self.baseline_captured: bool = False

    def capture_baseline(self, buffer_reader: Callable[[], Optional[str]], timeout_sec: float = 0.5):
        """Capture a readable baseline within a bounded adapter read."""
        raw = _read_before(buffer_reader, time.perf_counter() + max(0.0, timeout_sec))
        self.baseline_text = raw if raw is not None else ""
        self.baseline_captured = raw is not None
        self._baseline_attempted = True

    def observe_delivery(
        self,
        stop_timestamp: float,
        buffer_reader: Callable[[], Optional[str]],
        dispatch_timestamp: Optional[float] = None,
        injected_text: Optional[str] = None,
        timeout_sec: float = 3.0,
        settle_window_sec: float = 0.20,
        poll_interval_sec: float = 0.01,
        observation_method: str = "custom_reader"
    ) -> DeliveryObservationRecord:
        """Observe pure insertions; injected_text is the dispatched transcript payload.

        A callback supplies document content, not proof of foreground identity.
        Unrelated edits therefore cannot establish WRONG_TARGET.
        """
        deadline = stop_timestamp + max(0.0, timeout_sec)
        if not getattr(self, "_baseline_attempted", False):
            self.capture_baseline(buffer_reader, max(0.0, deadline - time.perf_counter()))
        record = DeliveryObservationRecord(
            trial_id=self.trial_id, target_app=self.target_app,
            target_hwnd=self.target_hwnd, baseline_text=self.baseline_text,
            stop_action_timestamp=stop_timestamp, dispatch_timestamp=dispatch_timestamp,
            observation_method=observation_method)

        def unverified(reason):
            record.status = ObservedDeliveryStatus.UNVERIFIED_DISPATCH
            record.missing_data_reason = reason
            return record

        if not self.baseline_captured:
            return unverified("Baseline unreadable or read deadline exceeded; delivery cannot be measured.")
        first = None
        changed = None
        previous = self.baseline_text
        delta = ""
        candidate = False
        is_dup = False
        while time.perf_counter() < deadline:
            # Do not start another callback in the final scheduling sliver.
            if deadline - time.perf_counter() <= 0.001:
                break
            current = _read_before(buffer_reader, deadline)
            now = time.perf_counter()
            if current is None:
                return unverified("Target document unreadable or read deadline exceeded.")

            # If text returns to baseline, any earlier candidate has disappeared:
            # reset settlement tracking.
            if current == self.baseline_text:
                first = None
                changed = None
                candidate = False
                previous = current
                delta = ""
                time.sleep(min(max(0.001, poll_interval_sec), max(0.0, deadline - now)))
                continue

            if current != previous:
                changed = now
                previous = current
            delta = _insertion_delta(self.baseline_text, current)
            is_dup = _is_duplicate_injection(delta, injected_text)
            # Correlate only newly inserted text, never a token already in the baseline.
            candidate = bool(delta) and (
                injected_text is None
                or delta == injected_text
                or injected_text.startswith(delta)
                or is_dup
            )
            if candidate and first is None:
                first = now
            if candidate and changed is not None and now - changed >= max(0.0, settle_window_sec):
                if injected_text is not None and delta != injected_text:
                    if is_dup:
                        record.status = ObservedDeliveryStatus.DUPLICATE_DELIVERY
                    elif injected_text.startswith(delta):
                        # A stable prefix is still incomplete; allow later chunks until deadline.
                        time.sleep(min(max(0.001, poll_interval_sec), max(0.0, deadline - now)))
                        continue
                    else:
                        time.sleep(min(max(0.001, poll_interval_sec), max(0.0, deadline - now)))
                        continue
                else:
                    record.status = ObservedDeliveryStatus.VERIFIED_FIRST_DELIVERY
                record.first_observed_timestamp = first
                record.stop_to_first_visible_ms = max(0.0, (first - stop_timestamp) * 1000.0)
                record.settled_observed_timestamp = changed
                record.stop_to_settled_visible_ms = max(0.0, (changed - stop_timestamp) * 1000.0)
                record.observed_text_delta = delta
                return record
            time.sleep(min(max(0.001, poll_interval_sec), max(0.0, deadline - now)))
        if candidate and first is not None:
            if is_dup:
                record.status = ObservedDeliveryStatus.DUPLICATE_DELIVERY
                record.first_observed_timestamp = first
                record.stop_to_first_visible_ms = max(0.0, (first - stop_timestamp) * 1000.0)
                record.settled_observed_timestamp = changed or first
                record.stop_to_settled_visible_ms = max(0.0, ((changed or first) - stop_timestamp) * 1000.0)
                record.observed_text_delta = delta
            elif injected_text and injected_text.startswith(delta):
                record.status = ObservedDeliveryStatus.PARTIAL_DELIVERY
                record.first_observed_timestamp = first
                record.stop_to_first_visible_ms = max(0.0, (first - stop_timestamp) * 1000.0)
                record.observed_text_delta = delta
                record.missing_data_reason = "Correlated inserted text was incomplete or did not settle before deadline."
            else:
                record.status = ObservedDeliveryStatus.TIMEOUT
                record.missing_data_reason = "No correlated insertion remained before the observation deadline."
        else:
            record.status = ObservedDeliveryStatus.TIMEOUT
            record.missing_data_reason = "No correlated insertion remained before the observation deadline."
        return record


def summarize_observed_deliveries(records: List[DeliveryObservationRecord]) -> Dict[str, Any]:
    """
    Aggregates delivery observations, strictly isolating verified deliveries
    from unreadable/timeout/refused trials.
    """
    total = len(records)
    verified = [r for r in records if r.status == ObservedDeliveryStatus.VERIFIED_FIRST_DELIVERY and r.stop_to_first_visible_ms is not None]
    unverified = [r for r in records if r.status == ObservedDeliveryStatus.UNVERIFIED_DISPATCH]
    refused = [r for r in records if r.status == ObservedDeliveryStatus.SAFE_REFUSAL]
    timed_out = [r for r in records if r.status == ObservedDeliveryStatus.TIMEOUT]

    first_latencies = sorted([r.stop_to_first_visible_ms for r in verified])
    settled_latencies = sorted([r.stop_to_settled_visible_ms for r in verified if r.stop_to_settled_visible_ms is not None])

    def _percentile(data: List[float], p: float) -> Optional[float]:
        if not data:
            return None
        k = (len(data) - 1) * p
        f = int(k)
        c = min(f + 1, len(data) - 1)
        d0 = data[f] * (c - k)
        d1 = data[c] * (k - f)
        return round(data[f] if f == c else d0 + d1, 2)

    return {
        "total_trials": total,
        "verified_count": len(verified),
        "unverified_count": len(unverified),
        "refused_count": len(refused),
        "timeout_count": len(timed_out),
        "verified_first_delivery_rate": round(len(verified) / total, 4) if total > 0 else 0.0,
        "first_visible_p50_ms": _percentile(first_latencies, 0.50),
        "first_visible_p95_ms": _percentile(first_latencies, 0.95),
        "settled_visible_p50_ms": _percentile(settled_latencies, 0.50),
        "settled_visible_p95_ms": _percentile(settled_latencies, 0.95),
    }
