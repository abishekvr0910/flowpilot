# 0003. Visible Delivery Benchmark Observer and Latency Contract

**Date:** 2026-10-24
**Status:** In Progress (P2)
**Audience:** FlowPilot maintainers, Codex, Gemini
**Baseline:** commit `6555e3dc9cd507b5fbc31d71f3d0be95d1c4078a` (v3.1.0-RC3)
**Scope Item:** Feature 29 (Competitive Evaluation & Runtime Visible Delivery Observation)

---

## 1. Summary

Measuring end-to-end user latency for dictation requires observing the exact instant text appears in the target document, not merely when FlowPilot finishes internal transcription or calls `TextInjector.inject_with_status()`.

Production dictation in FlowPilot deliberately preserves `stop_action_to_visible_text_ms: None` and `visible_delivery_status: "not_measured"` because non-invasive dictation tools cannot constantly inspect external applications without security, privacy, and performance violations.

To measure actual visible delivery latency fairly for competitive validation, this specification establishes:
1. An isolated, high-precision benchmarking observer module: `benchmarks/delivery_observer.py`.
2. A strict **delivery observation schema** recording stop action, acoustic endpoint, first observed text change, and settled completion.
3. Decoupling of **delivery observation** from **acoustic transcription accuracy** (a wrong transcription that appears in the document is a successful delivery with low word accuracy).
4. Truthful handling of unreadable targets, focus switches, duplicate deliveries, and recovery retries.
5. Comprehensive test fixtures covering all required delivery edge cases.

---

## 2. Timing Boundaries & Precision Contract

All timestamps use `time.perf_counter()` on the same system monotonic clock.

```text
[Dictation Stop Event] ----------------- T_stop
         |
         | (Local STT & Processing Pipeline)
         v
[Injector Dispatch] -------------------- T_dispatch
         |
         | (Windows Message Queue / Clipboard Paste / Target Process Rendering)
         v
[Target First Visible Change] ---------- T_first_visible
         |
         | (Settlement window: e.g. 100ms with no further text change)
         v
[Target Settled Text] ------------------ T_settled_visible
```

### Metrics Derived:
- `stop_to_first_visible_ms`: `(T_first_visible - T_stop) * 1000.0`
- `stop_to_settled_visible_ms`: `(T_settled_visible - T_stop) * 1000.0`
- `dispatch_to_first_visible_ms`: `(T_first_visible - T_dispatch) * 1000.0`

If no change is observed or the target is unreadable, latency is `None` (NEVER `0.0` or synthetic values).

---

## 3. Data Contract

### 3.1 Delivery Status Enum

```python
class ObservedDeliveryStatus(str, Enum):
    VERIFIED_FIRST_DELIVERY = "VERIFIED_FIRST_DELIVERY"  # Delivered on initial attempt into verified target
    UNVERIFIED_DISPATCH = "UNVERIFIED_DISPATCH"          # Keystroke dispatched, target buffer unreadable
    SAFE_REFUSAL = "SAFE_REFUSAL"                        # Target lost or guarded; aborted without dispatch
    PARTIAL_DELIVERY = "PARTIAL_DELIVERY"                # Text appeared but was truncated before settlement
    WRONG_TARGET = "WRONG_TARGET"                        # Focus shifted; text delivered into wrong window
    DUPLICATE_DELIVERY = "DUPLICATE_DELIVERY"            # Repeated insertion detected
    RECOVERED_DELIVERY = "RECOVERED_DELIVERY"            # Initial paste failed; explicit user recovery succeeded
    CANCELLED = "CANCELLED"                              # Dictation session cancelled before injection
    TIMEOUT = "TIMEOUT"                                  # No text change detected within observation deadline
```

### 3.2 Observation Record Schema

```python
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
    observation_method: str = "win32_edit"  # "win32_edit", "uia_readback", "buffer_callback", "mock_fixture"
```

---

## 4. Observer Algorithm & Settlement Policy

1. **Baseline Capture (`capture_baseline(reader, timeout_sec=0.5)`)**:
   Reads the exact document text before delivery. A missing, invalid, failed, or timed out read does not become an empty baseline. That trial remains `UNVERIFIED_DISPATCH` with no latency. Capture an explicit baseline before dispatch for meaningful trials.
2. **Observation deadline**:
   The deadline is `stop_timestamp + timeout_sec`, including every callback read and polling delay. Reads use daemon workers with four process wide concurrency slots. A timed out callback retains its slot until it actually returns. Further calls fail as unverified when all slots are occupied. Python cannot cancel a blocked callback, but abandoned work cannot grow beyond this bound or block interpreter exit.
3. **Insertion and payload correlation**:
   Extract only a pure insertion by excluding the unchanged baseline prefix and suffix. Existing text is never evidence of a newly delivered payload. Deletions, replacements, and unrelated edits cannot establish successful delivery. `injected_text` means the actual dispatched transcript payload, never the speech accuracy reference. When omitted, an insertion can be measured, but attribution depends on the isolated benchmark fixture.
4. **Settlement**:
   Every document change, including return to baseline, restarts the stability window. A complete payload must remain stable for `settle_window_sec` (default 0.20 seconds). The settled timestamp is the last observed change time, confirmed retrospectively after stability. Exact repeated payload insertion is `DUPLICATE_DELIVERY`. An incomplete payload prefix waits for further chunks until the deadline, then becomes `PARTIAL_DELIVERY`. A payload that disappears back to baseline does not become successful or partial delivery.
5. **Truthful outcomes**:
   A read failure at any point is `UNVERIFIED_DISPATCH` with no latency. A readable target with no correlated insertion remaining at the deadline is `TIMEOUT`. A correlated insertion still present but incomplete or unstable is `PARTIAL_DELIVERY`. An unrelated edit cannot prove `WRONG_TARGET`, because content alone does not establish window identity. Enum values for refusal, recovery, cancellation, and wrong target remain available for future adapters, but this callback observer cannot infer them.
6. **Adapter boundary**:
   This module is a benchmark callback observer only. No real target document adapter or foreground identity verifier is implemented. These tests validate isolated synthetic readers, not actual rendered pixels, Windows delivery, or production visible latency. Production telemetry remains unmeasured. No background surveillance or OS input is added.

---

## 5. Edge Cases & Truthfulness Matrix

| Scenario | Observer Status | Reported Latency | Delta Text |
|---|---|---|---|
| **Clean First-Attempt Paste** | `VERIFIED_FIRST_DELIVERY` | Observed ms from stop to sampled appearance | New inserted string |
| **Wrong Transcription Delivered** | `VERIFIED_FIRST_DELIVERY` | Observed ms (valid delivery) | Transcribed words (scored separately) |
| **Identical Text Already Present** | `TIMEOUT` (or verified only if count increases) | `None` if count unchanged | Empty |
| **Unreadable Target (Console / Remote)** | `UNVERIFIED_DISPATCH` | `None` (explicitly unmeasured) | `""` |
| **Focus Lost Before Paste** | `SAFE_REFUSAL` | `None` (preserved in recovery) | `""` |
| **Recovery Paste After Failure** | `RECOVERED_DELIVERY` | Measured separately as recovery | Recovered text |
| **Two Successive Identical Utterances** | `VERIFIED_FIRST_DELIVERY` | Measures new second addition | Second utterance string |
| **Cancelled Session** | `CANCELLED` | `None` | `""` |

---

## 6. Verification & Test Matrix

New unit test suite: `tests/test_delivery_observer.py` (wired into `tests/run_all_tests.py`).

1. `test_observer_measures_first_and_settled_appearance`: Verifies millisecond accuracy with calibrated synthetic delays.
2. `test_preexisting_identical_text_not_counted_as_delivery`: Baseline text is not misclassified as new text.
3. `test_wrong_transcription_is_valid_delivery`: Model error does not invalidate delivery timing.
4. `test_unreadable_target_returns_unverified_dispatch_with_none_latency`: Unreadable buffer preserves truthful `None` latency.
5. `test_timeout_leaves_latency_none`: Timeout does not produce synthetic zero or fallback latency.
6. `test_incremental_output_settlement`: Observes progressive typing chunks and settles on final completion.
7. Refusal and focus identity verification require an actual target adapter and remain outside this callback observer.
8. Regression fixtures cover unreadable baselines, insertion within existing text, duplicate and partial payloads, return to baseline, bounded stalled readers, elapsed stop deadlines, and singleton percentiles.

Targeted verification on 2026-10-24: `python -X utf8 tests/test_delivery_observer.py`, 17 tests passed.
