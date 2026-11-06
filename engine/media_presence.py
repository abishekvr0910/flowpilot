"""Feature 27: local media audio presence for smart companion hiding.

Answers one question per sample: is any audible render-session playback active
right now? The signal is the Windows audio session API (pycaw), the same surface
`engine/audio_ducker.py` already uses. It never reads window titles, screen
pixels, or recognizable content, and it never ties playback to a foreground
window; a muted or paused stream does not count as audible. Fails soft: any
COM or platform error permanently disables the probe for the process lifetime
instead of breaking the visibility tick.

Feature 27b: Capture Session Monitoring ("Smart Pause During Calls")

Enumerates active capture sessions (eCapture endpoints) via IAudioSessionManager2
to detect when communication applications (Zoom, Teams, Discord, Meet, Slack, etc.)
are actively capturing the microphone. When a call holds the microphone, FlowPilot
can automatically pause dictation to prevent accidental transcription leaks.
"""

import logging
import threading
import time
from typing import Callable, List, NamedTuple, Optional, Set

log = logging.getLogger("FlowPilot.MediaPresence")

PEAK_THRESHOLD = 0.02
GRACE_SECONDS = 1.5
SUSTAIN_SECONDS = 1.0

# Communication applications that typically hold the microphone during calls
CALL_PROCESS_NAMES: Set[str] = frozenset({
    "zoom.exe", "zoom.workplace.exe", "teams.exe", "ms-teams.exe",
    "discord.exe", "discordcanary.exe", "discordptb.exe",
    "slack.exe", "slack-app.exe",
    "webex.exe", "webexhost.exe", "webexmeetings.exe",
    "gotomeeting.exe", "gotowebinar.exe",
    "skype.exe", "lync.exe", "communicator.exe",
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe",  # Browser-based Meet/Teams
    "facetime.exe", "facetimehd.exe",
    "teams.exe", "msteams.exe",
    "googlemeet.exe", "meet.exe",
})


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
    linger grace keeps the hide stable through momentary pauses. The production
    sampler calls this probe off the Qt thread. `provider` and `clock` are
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
        self._cached_speakers = None
        self._cached_master_meter = None
        self._last_speaker_query_ts = 0.0

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
        if self._established and (now - self._last_peak_ts) < self.grace_seconds:
            return True
        self._established = False
        return False

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
            try:
                comtypes.CoInitialize()
                co_init = True
            except Exception:
                pass
            samples: List[SessionSample] = []

            # Refresh speaker endpoint reference once every 10 seconds or on failure
            now = time.monotonic()
            if self._cached_speakers is None or (now - self._last_speaker_query_ts > 10.0):
                try:
                    self._cached_speakers = AudioUtilities.GetSpeakers()
                    self._last_speaker_query_ts = now
                    if self._cached_speakers and hasattr(self._cached_speakers, "_dev") and self._cached_speakers._dev:
                        m_act = self._cached_speakers._dev.Activate(IAudioMeterInformation._iid_, comtypes.CLSCTX_ALL, None)
                        self._cached_master_meter = m_act.QueryInterface(IAudioMeterInformation)
                    else:
                        self._cached_master_meter = None
                except Exception:
                    self._cached_speakers = None
                    self._cached_master_meter = None

            speakers = self._cached_speakers
            endpoint_muted = False
            if speakers and speakers.EndpointVolume:
                try:
                    endpoint_muted = bool(speakers.EndpointVolume.GetMute())
                except Exception:
                    self._cached_speakers = None
                    self._cached_master_meter = None
            if endpoint_muted:
                return samples

            # Master endpoint peak gate: avoid expensive session enumeration if hardware is silent
            if self._cached_master_meter:
                try:
                    if float(self._cached_master_meter.GetPeakValue()) <= PEAK_THRESHOLD:
                        return samples
                except Exception:
                    self._cached_speakers = None
                    self._cached_master_meter = None

            my_pid = os.getpid()
            for session in AudioUtilities.GetAllSessions():
                pid = int(getattr(session, "ProcessId", 0) or 0)
                if pid == my_pid:
                    continue
                volume = 1.0
                simple = getattr(session, "SimpleAudioVolume", None)
                if simple is not None:
                    try:
                        if bool(simple.GetMute()):
                            continue
                        volume = float(simple.GetMasterVolume())
                    except Exception:
                        # Unknown volume state is not evidence of audible media.
                        continue
                if volume <= 0.0:
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


class CaptureSessionMonitor:
    """Monitors active capture (microphone) sessions to detect ongoing calls.

    Uses IAudioSessionManager2 on eCapture endpoints to enumerate sessions.
    When a known communication application holds an active capture session,
    returns True to indicate a call is in progress. Fails soft: any COM error
    permanently disables the probe for the process lifetime.
    """

    def __init__(
        self,
        call_process_names: Optional[Set[str]] = None,
        provider: Optional[Callable[[], bool]] = None,
    ):
        self._call_process_names = call_process_names or CALL_PROCESS_NAMES
        self._provider = provider or self._pycaw_provider
        self._unavailable = False

    def is_call_active(self) -> bool:
        """Returns True if a known communication app is actively capturing."""
        if self._unavailable:
            return False
        try:
            return self._provider()
        except Exception as exc:
            self._unavailable = True
            log.warning("Capture session monitor disabled after error: %s", exc)
            return False

    def _pycaw_provider(self) -> bool:
        import comtypes
        from pycaw.pycaw import AudioUtilities
        from comtypes import CLSCTX_ALL

        co_init = False
        try:
            try:
                comtypes.CoInitialize()
                co_init = True
            except Exception:
                pass

            # eCapture = 0 (capture/microphone endpoints)
            from comtypes.gen import MMDeviceAPI
            enumerator = comtypes.CoCreateInstance(
                MMDeviceAPI.MMDeviceEnumerator._reg_clsid_,
                None,
                CLSCTX_ALL,
                MMDeviceAPI.IMMDeviceEnumerator._iid_,
            )
            endpoints = enumerator.EnumAudioEndpoints(MMDeviceAPI.eCapture, MMDeviceAPI.DEVICE_STATE_ACTIVE)

            # Get IAudioSessionManager2 for each active capture endpoint
            for i in range(endpoints.GetCount()):
                endpoint = endpoints.Item(i)
                session_manager = endpoint.Activate(
                    MMDeviceAPI.IAudioSessionManager2._iid_,
                    CLSCTX_ALL,
                    None,
                ).QueryInterface(MMDeviceAPI.IAudioSessionManager2)

                session_enumerator = session_manager.GetSessionEnumerator()
                for j in range(session_enumerator.GetCount()):
                    session_control = session_enumerator.GetSession(j)
                    session_control2 = session_control.QueryInterface(MMDeviceAPI.IAudioSessionControl2)

                    # Get process ID and state
                    pid = session_control2.GetProcessId()
                    state = session_control.GetState()

                    # AudioSessionStateActive = 1
                    if state == 1 and pid > 0:
                        try:
                            import psutil
                            proc = psutil.Process(pid)
                            proc_name = proc.name().lower()
                            if proc_name in self._call_process_names:
                                log.debug("Active capture session detected: %s (PID %d)", proc_name, pid)
                                return True
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
            return False
        except Exception:
            raise
        finally:
            if co_init:
                try:
                    comtypes.CoUninitialize()
                except Exception:
                    pass


class SampledCaptureMonitor:
    """Keep the potentially slow Windows audio query off the Qt event loop."""

    def __init__(self, probe=None, interval_seconds: float = 1.0):
        self._probe = probe if probe is not None else CaptureSessionMonitor()
        self._interval_seconds = interval_seconds
        self._active = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run, name="FlowPilotCaptureMonitor", daemon=True,
            )
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        with self._lock:
            self._active = False
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=0.1)

    def is_call_active(self) -> bool:
        with self._lock:
            return self._active

    def _run(self):
        import comtypes
        co_init = False
        try:
            comtypes.CoInitialize()
            co_init = True
        except Exception:
            pass

        try:
            while not self._stop_event.is_set():
                try:
                    active = self._probe.is_call_active()
                except Exception as exc:
                    log.warning("Capture monitor sampler stopped after error: %s", exc)
                    active = False
                    self._stop_event.set()
                with self._lock:
                    self._active = active and not self._stop_event.is_set()
                self._stop_event.wait(self._interval_seconds)
        finally:
            if co_init:
                try:
                    comtypes.CoUninitialize()
                except Exception:
                    pass


class NullCaptureMonitor:
    """Hermetic default: never reports active call, never touches the OS."""

    def is_call_active(self) -> bool:
        return False

    def start(self):
        pass

    def stop(self):
        pass


class SampledMediaPresence:
    """Keep the potentially slow Windows audio query off the Qt event loop."""

    def __init__(self, probe=None, interval_seconds: float = 0.35):
        self._probe = probe if probe is not None else MediaAudioPresence()
        self._interval_seconds = interval_seconds
        self._active = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run, name="FlowPilotMediaPresence", daemon=True,
            )
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        with self._lock:
            self._active = False
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=0.1)

    def is_active(self) -> bool:
        with self._lock:
            return self._active

    def _run(self):
        import comtypes
        co_init = False
        try:
            comtypes.CoInitialize()
            co_init = True
        except Exception:
            pass

        try:
            while not self._stop_event.is_set():
                try:
                    active = self._probe.is_active()
                except Exception as exc:
                    log.warning("Media presence sampler stopped after error: %s", exc)
                    active = False
                    self._stop_event.set()
                with self._lock:
                    self._active = active and not self._stop_event.is_set()
                self._stop_event.wait(self._interval_seconds)
        finally:
            if co_init:
                try:
                    comtypes.CoUninitialize()
                except Exception:
                    pass
