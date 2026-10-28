"""
FlowPilot Dictation Session Module
Provides explicit session ownership, thread-safe state machine,
and cancellation guards for end-to-end voice dictation lifecycles.
"""

import time
import uuid
import threading
from enum import Enum
from typing import Dict, Any, Optional, List


class SessionState(str, Enum):
    IDLE = "IDLE"
    RECORDING = "RECORDING"
    FINALIZING = "FINALIZING"
    TRANSCRIBING = "TRANSCRIBING"
    VALIDATING = "VALIDATING"
    INJECTING = "INJECTING"
    SUCCESS = "SUCCESS"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


# Valid legal state transitions
LEGAL_TRANSITIONS = {
    SessionState.IDLE: {SessionState.RECORDING, SessionState.ERROR},
    SessionState.RECORDING: {SessionState.FINALIZING, SessionState.CANCELLED, SessionState.ERROR},
    SessionState.FINALIZING: {SessionState.TRANSCRIBING, SessionState.IDLE, SessionState.CANCELLED, SessionState.ERROR},
    SessionState.TRANSCRIBING: {SessionState.VALIDATING, SessionState.IDLE, SessionState.CANCELLED, SessionState.ERROR},
    SessionState.VALIDATING: {SessionState.INJECTING, SessionState.IDLE, SessionState.CANCELLED, SessionState.ERROR},
    SessionState.INJECTING: {SessionState.SUCCESS, SessionState.ERROR, SessionState.CANCELLED},
    SessionState.SUCCESS: {SessionState.IDLE},
    SessionState.CANCELLED: {SessionState.IDLE},
    SessionState.ERROR: {SessionState.IDLE},
}


class DictationSession:
    """
    Encapsulates the lifecycle, owned data, and state transitions of a single
    dictation interaction. Prevents late callbacks, overlapping recordings,
    and stale result injections.
    """

    def __init__(self, target_window_info: Optional[Dict[str, Any]] = None, tone_mode: str = "general"):
        self.session_id: str = f"fp-sess-{uuid.uuid4().hex[:8]}"
        self.created_at: float = time.time()
        self.created_perf: float = time.perf_counter()
        self.state: SessionState = SessionState.IDLE
        self._lock = threading.RLock()

        self.target_window_info: Dict[str, Any] = target_window_info or {}
        self.tone_mode: str = tone_mode
        self.language: str = "auto"
        self.task: str = "transcribe"
        self.is_selection_rewrite: bool = False
        self.selected_text: Optional[str] = None

        # Owned audio payload
        self.audio_bytes: Optional[bytes] = None
        self.audio_array: Optional[Any] = None
        self.audio_duration_sec: float = 0.0

        # Transcripts and validation
        self.raw_text: str = ""
        self.candidate_text: str = ""
        self.final_text: str = ""
        self.detected_language: str = "en"
        self.validation_result: Optional[Dict[str, Any]] = None

        # Injection details
        self.injection_method: str = ""
        self.injection_success: bool = False

        # Cancellation flag
        self.is_cancelled: bool = False
        self.cancel_reason: str = ""

        # Monotonic timing instrumentation
        self.timings: Dict[str, float] = {}

    def transition_to(self, new_state: SessionState) -> bool:
        """
        Thread-safely transitions to a new state if the transition is legal.
        Returns True if transition succeeded, False if illegal or session cancelled.
        """
        with self._lock:
            # If session is cancelled, it can only transition to CANCELLED or IDLE
            if self.is_cancelled and new_state not in (SessionState.CANCELLED, SessionState.IDLE):
                return False

            allowed = LEGAL_TRANSITIONS.get(self.state, set())
            if new_state in allowed or new_state in (SessionState.CANCELLED, SessionState.ERROR):
                self.state = new_state
                return True
            return False

    def cancel(self, reason: str = "user_cancelled") -> None:
        """Marks the session as cancelled, invalidating all downstream operations."""
        with self._lock:
            self.is_cancelled = True
            self.cancel_reason = reason
            self.state = SessionState.CANCELLED

    def is_active(self) -> bool:
        """Returns True if the session is currently in flight (not idle or terminal)."""
        with self._lock:
            return not self.is_cancelled and self.state in (
                SessionState.RECORDING,
                SessionState.FINALIZING,
                SessionState.TRANSCRIBING,
                SessionState.VALIDATING,
                SessionState.INJECTING,
            )

    def is_terminal(self) -> bool:
        """Returns True if the session has reached a final state."""
        with self._lock:
            return self.state in (SessionState.SUCCESS, SessionState.CANCELLED, SessionState.ERROR, SessionState.IDLE)

    def record_timing(self, stage_name: str, duration_ms: float) -> None:
        """Records monotonic timing for a specific stage."""
        with self._lock:
            self.timings[stage_name] = round(duration_ms, 2)
