"""Feature 25: local media audio presence for smart companion hiding.

Answers one question per sample: is any audible render-session playback active
right now? The signal is the Windows audio session API (pycaw), the same surface
`engine/audio_ducker.py` already uses. It never reads window titles, screen
pixels, or recognizable content, and it never ties playback to a foreground
window; a muted or paused stream does not count as audible. Fails soft: any
COM or platform error permanently disables the probe for the process lifetime
instead of breaking the visibility tick.
"""

import logging
import time
from typing import Callable, List, NamedTuple, Optional

log = logging.getLogger("FlowPilot.MediaPresence")

PEAK_THRESHOLD = 0.02
GRACE_SECONDS = 1.5
SUSTAIN_SECONDS = 1.0


class SessionSample(NamedTuple):
    pid: int
    process_name: str
    peak: float
    volume: float


class NullMediaPresence:
    """Hermetic default: never reports active, never touches the OS."""

    def is_active(self) -> bool:
        return False


class MediaAudioPresence:
    """Polls render sessions for audibly sustained playback.

    Only CONTINUOUS audibility counts: a one-off system sound that stops before
    the sustain window passes never hides the companion. Once sustained, a short
    linger grace keeps the hide stable through momentary pauses. Runs on the Qt
    main thread alongside the visibility tick. `provider` and `clock` are
    injection points for tests so no COM ever appears in suites.
    """

    def __init__(
        self,
        grace_seconds: float = GRACE_SECONDS,
        sustain_seconds: float = SUSTAIN_SECONDS,
        provider: Optional[Callable[[], List[SessionSample]]] = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.grace_seconds = grace_seconds
        self.sustain_seconds = sustain_seconds
        self._provider = provider or self._pycaw_provider
        self._clock = clock
        self._last_peak_ts = 0.0
        self._suspect_since = None
        self._established = False
        self._unavailable = False

    def is_active(self) -> bool:
        if self._unavailable:
            return False
        try:
            samples = self._provider()
        except Exception as exc:  # pycaw/COM failures disable the probe
            self._unavailable = True
            log.warning("Media presence probe disabled after error: %s", exc)
            return False
        now = self._clock()
        audible = any(self._sample_audible(s) for s in samples)
        if audible:
            self._last_peak_ts = now
            if not self._established:
                if self._suspect_since is None:
                    self._suspect_since = now
                if now - self._suspect_since >= self.sustain_seconds:
                    self._established = True
                return self._established
            return True
        self._suspect_since = None  # continuity is required for the sustain gate
        return self._established and (now - self._last_peak_ts) < self.grace_seconds

    def _sample_audible(self, sample: SessionSample) -> bool:
        if sample.volume <= 0.0:
            return False
        return sample.peak > PEAK_THRESHOLD

    def _pycaw_provider(self) -> List[SessionSample]:
        import os

        import comtypes
        from pycaw.pycaw import AudioUtilities
        from pycaw.pycaw import IAudioMeterInformation

        co_init = False
        try:
            comtypes.CoInitialize()
            co_init = True
            samples: List[SessionSample] = []
            speakers = AudioUtilities.GetSpeakers()
            endpoint_muted = False
            if speakers and speakers.EndpointVolume:
                endpoint_muted = bool(speakers.EndpointVolume.GetMute())
            if endpoint_muted:
                return samples
            my_pid = os.getpid()
            for session in AudioUtilities.GetAllSessions():
                pid = int(getattr(session, "ProcessId", 0) or 0)
                if pid == my_pid:
                    continue
                meter = None
                ctl = getattr(session, "_ctl", None)
                if ctl is None:
                    continue
                try:
                    meter = ctl.QueryInterface(IAudioMeterInformation)
                except Exception:
                    meter = None
                if meter is None:
                    continue
                try:
                    peak = float(meter.GetPeakValue())
                except Exception:
                    continue
                volume = 1.0
                simple = getattr(session, "SimpleAudioVolume", None)
                if simple is not None:
                    try:
                        volume = float(simple.GetMasterVolume())
                    except Exception:
                        volume = 1.0
                samples.append(SessionSample(pid, "", peak, volume))
            return samples
        except Exception:
            raise
        finally:
            if co_init:
                try:
                    comtypes.CoUninitialize()
                except Exception:
                    pass
