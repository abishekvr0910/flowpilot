"""Feature 32: Bounded, opt-in local dictation metrics without transcript text."""

import json
import logging
import ntpath
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger("FlowPilot.PilotTelemetry")
_WRITE_LOCK = threading.Lock()

_NUMERIC_FIELDS = frozenset({
    "timestamp", "audio_duration_sec", "stt_duration_sec", "format_duration_sec",
    "total_duration_sec", "stop_action_to_injection_result_ms",
    "acoustic_end_to_injection_result_ms", "stop_action_to_visible_text_ms",
    "char_count",
})
_TEXT_FIELDS = frozenset({
    "target_app", "injection_method", "injection_status", "visible_delivery_status",
})
_BOOLEAN_FIELDS = frozenset({"injection_confirmed", "injection_success"})


def _safe_event(data: Mapping[str, Any]) -> dict[str, Any]:
    """Allow measured metadata only; a caller cannot accidentally log a transcript."""
    event: dict[str, Any] = {}
    for key in _NUMERIC_FIELDS:
        value = data.get(key)
        if key in data and (value is None or (isinstance(value, (int, float)) and not isinstance(value, bool))):
            event[key] = value
    for key in _BOOLEAN_FIELDS:
        value = data.get(key)
        if isinstance(value, bool):
            event[key] = value
    for key in _TEXT_FIELDS:
        value = data.get(key)
        if isinstance(value, str):
            event[key] = (ntpath.basename(value) if key == "target_app" else value)[:64]
    return event


def append_local_event(
    data: Mapping[str, Any], directory: Path, *, max_bytes: int = 1_000_000,
    backups: int = 3,
) -> None:
    """Write one JSON line and rotate before the local log exceeds its limit."""
    event = _safe_event(data)
    if not event:
        return
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    with _WRITE_LOCK:
        handler = RotatingFileHandler(
            directory / "dictation_telemetry.log", maxBytes=max_bytes,
            backupCount=backups, encoding="utf-8", delay=True,
        )
        try:
            handler.emit(logging.makeLogRecord({"msg": line, "levelno": logging.INFO,
                                                "levelname": "INFO"}))
        finally:
            handler.close()
