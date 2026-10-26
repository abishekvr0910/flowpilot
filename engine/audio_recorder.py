"""Feature 28: Buffered capture with safe deferred microphone changes."""
import logging
import io
import time
import threading
import ctypes
import sys
import collections
import numpy as np
import sounddevice as sd
import soundfile as sf
from typing import Callable, Optional

logger = logging.getLogger("FlowPilot.AudioRecorder")

def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Fast linear interpolation resampling for multi-device audio compatibility."""
    if orig_sr == target_sr or len(audio) == 0:
        return audio
    duration = len(audio) / orig_sr
    target_len = int(round(duration * target_sr))
    orig_times = np.linspace(0, duration, len(audio), endpoint=False)
    target_times = np.linspace(0, duration, target_len, endpoint=False)
    if audio.ndim == 2:
        channels = [np.interp(target_times, orig_times, audio[:, ch]) for ch in range(audio.shape[1])]
        return np.column_stack(channels).astype(np.float32)
    return np.interp(target_times, orig_times, audio).astype(np.float32)

class AudioRecorder:
    CAPTURE_STALL_SECONDS = 2.0
    STREAM_CLOSE_SECONDS = 1.0
    STREAM_OPEN_SECONDS = 8.0

    def __init__(self, sample_rate: int = 16000, channels: int = 1, device: Optional[int] = None, device_index: Optional[int] = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device if device is not None else device_index
        self.capture_sample_rate = sample_rate
        self.is_recording = False
        self.audio_frames = []
        self.last_audio_array: Optional[np.ndarray] = None
        self.stream: Optional[sd.InputStream] = None
        self.level_callback: Optional[Callable[[float], None]] = None
        self._lock = threading.RLock()

        # Pre-roll circular ring buffer (prevents clipping the first syllable)
        self.preroll_seconds: float = 0.35
        self.enable_preroll: bool = True
        self._preroll_buffer: collections.deque = collections.deque()
        self._pending_device: Optional[int] = None
        self._device_change_pending: bool = False
        self._capture_error: Optional[str] = None
        self._last_callback_at: float = 0.0
        self._recording_started_at: float = 0.0
        self._stream_cleanup_failed: bool = False

    def get_state(self) -> dict:
        """Returns the current state dictionary of the audio recorder."""
        return {
            "state": "recording" if self.is_recording else "idle",
            "is_recording": self.is_recording,
            "sample_rate": self.sample_rate
        }

    def _audio_callback(self, indata, frames, time_info, status):
        try:
            self._last_callback_at = time.monotonic()
            if status:
                if self.is_recording:
                    self._capture_error = f"Microphone capture lost audio ({status}). Reconnect it and retry."

            if not self.is_recording:
                # Maintain rolling pre-roll buffer while idle so first word is never clipped
                if self.enable_preroll and frames > 0:
                    self._preroll_buffer.append(indata.copy())
                    max_chunks = max(1, int(self.capture_sample_rate * self.preroll_seconds / frames))
                    while len(self._preroll_buffer) > max_chunks:
                        self._preroll_buffer.popleft()
                return

            self.audio_frames.append(indata.copy())
            if self.level_callback:
                rms = np.sqrt(np.mean(indata**2))
                level = min(1.0, float(rms * 10.0))
                self.level_callback(level)
        except Exception as exc:
            self._capture_error = f"Microphone capture callback failed ({type(exc).__name__}). Reconnect it and retry."

    def capture_health_error(self) -> Optional[str]:
        """Read callback health without taking the recorder lock or calling the driver."""
        if self._stream_cleanup_failed:
            return "Microphone driver did not release its stream. Restart FlowPilot before recording again."
        if not self.is_recording:
            return None
        if self._capture_error:
            return self._capture_error
        if self.stream is None:
            return "Microphone stream disappeared during recording. Reconnect it and retry."
        last_seen = max(self._recording_started_at, self._last_callback_at)
        if last_seen and time.monotonic() - last_seen > self.CAPTURE_STALL_SECONDS:
            return "Microphone stopped delivering audio. Reconnect it and retry."
        return None

    def has_healthy_hot_stream(self) -> bool:
        """Return True only if an open pre-roll stream is active and not stalled."""
        if not self.stream or not getattr(self.stream, "active", False):
            return False
        if self._stream_cleanup_failed or self._capture_error:
            return False
        if self._last_callback_at > 0 and (time.monotonic() - self._last_callback_at) > self.CAPTURE_STALL_SECONDS:
            return False
        return True

    def _release_stream_bounded(self, stream) -> bool:
        """Keep an unresponsive PortAudio driver off the Qt and dictation threads."""
        finished = threading.Event()
        close_failed = threading.Event()

        def release():
            com_initialized = False
            if sys.platform == "win32":
                try:
                    ctypes.windll.ole32.CoInitializeEx(None, 0)
                    com_initialized = True
                except Exception:
                    pass
            try:
                if hasattr(stream, "abort"):
                    stream.abort()
                else:
                    stream.stop()
            except Exception as exc:
                logger.warning("Microphone stream abort failed: %s", exc)
            try:
                stream.close()
            except Exception as exc:
                close_failed.set()
                logger.warning("Microphone stream close failed: %s", exc)
            finally:
                if com_initialized:
                    try:
                        ctypes.windll.ole32.CoUninitialize()
                    except Exception:
                        pass
                finished.set()

        threading.Thread(target=release, daemon=True, name="FlowPilot-MicRelease").start()
        if not finished.wait(self.STREAM_CLOSE_SECONDS):
            self._stream_cleanup_failed = True
            logger.error("Microphone driver did not release its stream within %.1f seconds", self.STREAM_CLOSE_SECONDS)
            return False
        if close_failed.is_set():
            self._stream_cleanup_failed = True
            return False
        return True

    def _open_stream_bounded(self, sample_rate: int, channels: Optional[int] = None):
        """Open PortAudio outside the recorder lock's thread with a hard deadline."""
        finished = threading.Event()
        result_lock = threading.Lock()
        result = {"stream": None, "error": None, "cancelled": False}
        stream_channels = self.channels if channels is None else channels

        def open_stream():
            com_initialized = False
            if sys.platform == "win32":
                try:
                    ctypes.windll.ole32.CoInitializeEx(None, 0)
                    com_initialized = True
                except Exception:
                    pass
            stream = None
            error = None
            try:
                stream = sd.InputStream(
                    samplerate=sample_rate, channels=stream_channels, dtype="float32",
                    device=self.device, callback=self._audio_callback,
                )
                stream.start()
            except Exception as exc:
                error = exc
            with result_lock:
                if result["cancelled"] or error is not None:
                    stale_stream = stream
                else:
                    stale_stream = None
                    result["stream"] = stream
                result["error"] = error
            if stale_stream is not None:
                self._release_stream_bounded(stale_stream)
            if com_initialized:
                try:
                    ctypes.windll.ole32.CoUninitialize()
                except Exception:
                    pass
            finished.set()

        threading.Thread(target=open_stream, daemon=True, name="FlowPilot-MicOpen").start()
        if not finished.wait(self.STREAM_OPEN_SECONDS):
            with result_lock:
                result["cancelled"] = True
                late_stream = result["stream"]
                result["stream"] = None
            if late_stream is not None:
                self._release_stream_bounded(late_stream)
            self._stream_cleanup_failed = True
            raise RuntimeError(
                f"Microphone driver did not open within {self.STREAM_OPEN_SECONDS:g} seconds. "
                "Restart FlowPilot before recording again."
            )
        if result["error"] is not None:
            raise result["error"]
        return result["stream"]

    def _warmup_stream_locked(self):
        if self._stream_cleanup_failed:
            logger.warning("Microphone warmup refused after an unresponsive driver shutdown")
            return
        if self.device is not None and self.device < 0:
            print(f"[Audio] Selected audio device is missing/disconnected (device={self.device}). Warmup stream skipped.")
            return
        if self.stream and getattr(self.stream, "active", False):
            return
        try:
            self.capture_sample_rate = self.sample_rate
            self.stream = self._open_stream_bounded(self.sample_rate)
            print(f"[Audio] Pre-roll stream warmed up and monitoring on device {self.device}.")
        except Exception as exc:
            failed_stream = self.stream
            self.stream = None
            if failed_stream:
                self._release_stream_bounded(failed_stream)
            logger.warning("Microphone warmup deferred: %s", exc)

    def warmup_stream(self):
        """Pre-arms the PortAudio stream at startup so recording starts with zero latency and hot pre-roll."""
        with self._lock:
            self._warmup_stream_locked()

    def start_recording(self):
        with self._lock:
            if self.is_recording:
                return
            if self.sample_rate <= 0:
                raise ValueError(f"Invalid sample rate: {self.sample_rate}")
            if self.device is not None and self.device < 0:
                self.is_recording = False
                raise RuntimeError(f"Selected audio input device is missing or disconnected (device={self.device}).")
            if self._stream_cleanup_failed:
                raise RuntimeError(self.capture_health_error())
            self._capture_error = None
            self._recording_started_at = time.monotonic()

            # 1. If stream is already hot and running (and not stalled by an idle unplug), start immediately!
            if self.has_healthy_hot_stream():
                if self.enable_preroll and self._preroll_buffer:
                    self.audio_frames = list(self._preroll_buffer)
                    self._preroll_buffer.clear()
                else:
                    self.audio_frames = []
                self.last_audio_array = None
                self.is_recording = True
                print(f"[Audio] Recording started with hot stream (pre-roll: {len(self.audio_frames)} chunks)...")
                return

            # 2. Otherwise start a new stream
            if self.stream:
                stale_stream = self.stream
                self.stream = None
                if not self._release_stream_bounded(stale_stream):
                    raise RuntimeError(self.capture_health_error())

            if self.enable_preroll and self._preroll_buffer:
                self.audio_frames = list(self._preroll_buffer)
                self._preroll_buffer.clear()
            else:
                self.audio_frames = []
            self.last_audio_array = None
            self.capture_sample_rate = self.sample_rate
            self.is_recording = True

            try:
                # First attempt: Target sample rate (16000Hz)
                self.stream = self._open_stream_bounded(self.sample_rate)
                self._recording_started_at = time.monotonic()
                print("[Audio] Recording started...")
            except Exception as e:
                if self._stream_cleanup_failed:
                    self.is_recording = False
                    raise RuntimeError(self.capture_health_error()) from e
                failed_stream = self.stream
                self.stream = None
                if failed_stream and not self._release_stream_bounded(failed_stream):
                    self.is_recording = False
                    raise RuntimeError(self.capture_health_error()) from e
                # Fallback attempt: If hardware requires 44.1kHz/48kHz or stereo WASAPI mix format, query native format
                fallback_success = False
                try:
                    dev_info = sd.query_devices(self.device, "input")
                    native_sr = int(dev_info.get("default_samplerate", 44100))
                    max_ch = int(dev_info.get("max_input_channels", self.channels) or self.channels)
                    candidate_formats = []
                    if native_sr > 0 and native_sr != self.sample_rate:
                        candidate_formats.append((native_sr, self.channels))
                    if max_ch > self.channels:
                        candidate_formats.append((native_sr if native_sr > 0 else self.sample_rate, min(2, max_ch)))
                    for cand_sr, cand_ch in candidate_formats:
                        try:
                            print(f"[Audio] Target format ({self.sample_rate}Hz, {self.channels}ch) rejected. Falling back to native ({cand_sr}Hz, {cand_ch}ch) with dynamic resampling.")
                            self.capture_sample_rate = cand_sr
                            self.stream = self._open_stream_bounded(cand_sr, channels=cand_ch)
                            self._recording_started_at = time.monotonic()
                            fallback_success = True
                            print("[Audio] Recording started with native hardware format fallback.")
                            break
                        except Exception:
                            if self._stream_cleanup_failed:
                                break
                except Exception:
                    pass

                if not fallback_success:
                    if self._stream_cleanup_failed:
                        self.is_recording = False
                        raise RuntimeError(self.capture_health_error()) from e
                    failed_stream = self.stream
                    self.stream = None
                    if failed_stream and not self._release_stream_bounded(failed_stream):
                        self.is_recording = False
                        raise RuntimeError(self.capture_health_error()) from e
                    self.is_recording = False
                    print(f"[Audio Error] Failed to start stream: {e}")
                    raise e

    def stop_recording(self, keep_stream_alive: bool = True) -> Optional[bytes]:
        with self._lock:
            health_error = None
            try:
                if not self.is_recording and not self.stream:
                    return None
                health_error = self.capture_health_error()
                self.is_recording = False
                if (not keep_stream_alive or health_error) and self.stream:
                    old_stream = self.stream
                    self.stream = None
                    if not self._release_stream_bounded(old_stream):
                        health_error = self.capture_health_error()
                if health_error:
                    self.audio_frames = []
                    self.last_audio_array = None
                    raise RuntimeError(health_error)

                if not self.audio_frames:
                    print("[Audio] No audio frames captured.")
                    self.last_audio_array = None
                    return None

                # Concatenate frames and downmix multi-channel WASAPI capture to mono if needed
                recording = np.concatenate(self.audio_frames, axis=0)
                self.audio_frames = []
                if recording.ndim == 2 and recording.shape[1] > 1 and self.channels == 1:
                    recording = np.mean(recording, axis=1, keepdims=True).astype(np.float32)

                # Check duration
                duration = len(recording) / self.capture_sample_rate
                if duration < 0.3:
                    print(f"[Audio] Recording too short ({duration:.2f}s). Ignoring.")
                    self.last_audio_array = None
                    return None

                # Resample to standard 16kHz if captured at fallback native rate
                if self.capture_sample_rate != self.sample_rate:
                    recording = resample_audio(recording, self.capture_sample_rate, self.sample_rate)

                # Store 1D contiguous float32 numpy array at 16kHz for zero-copy faster-whisper inference
                clean_arr = np.ascontiguousarray(recording.squeeze(), dtype=np.float32)
                self.last_audio_array = clean_arr

                # Convert to 16-bit PCM WAV in-memory buffer
                buffer = io.BytesIO()
                sf.write(buffer, recording, self.sample_rate, format="WAV", subtype="PCM_16")
                wav_bytes = buffer.getvalue()
                print(f"[Audio] Captured {duration:.2f}s of audio ({len(wav_bytes)} bytes)")
                return wav_bytes
            finally:
                if (getattr(self, "_device_change_pending", False)
                        and not self._stream_cleanup_failed and not health_error):
                    pending = self._pending_device
                    self._device_change_pending = False
                    self._pending_device = None
                    self.set_device(pending, warmup=keep_stream_alive)

    def set_device(self, device: Optional[int], defer_if_recording: bool = False, *, warmup: bool = True):
        """Updates the input audio capture device and dynamically re-warms the stream."""
        with self._lock:
            if self.device == device and ((self.stream and getattr(self.stream, "active", False))
                                          or (defer_if_recording and self.is_recording)):
                self._device_change_pending = False
                self._pending_device = None
                return
            if defer_if_recording and self.is_recording:
                print(f"[Audio] Recording active; deferring audio device switch to index {device} until recording stops.")
                self._pending_device = device
                self._device_change_pending = True
                return
            self.device = device
            self._pending_device = None
            self._device_change_pending = False
            was_recording = self.is_recording
            existing_frames = list(self.audio_frames) if was_recording else []
            if self.stream:
                old_stream = self.stream
                self.stream = None
                if not self._release_stream_bounded(old_stream):
                    raise RuntimeError(self.capture_health_error())
            self._preroll_buffer.clear()
            if self.device is not None and self.device < 0:
                print(f"[Audio] Input device switched to missing/disconnected state (device={self.device}).")
                if was_recording:
                    self.is_recording = False
                return
            if was_recording:
                self.is_recording = False
                self.start_recording()
                # Preserve all audio frames captured prior to the device switch
                self.audio_frames = existing_frames + self.audio_frames
            elif warmup:
                self._warmup_stream_locked()

    def close(self):
        """Cleanly terminates and releases the underlying audio device."""
        with self._lock:
            self.is_recording = False
            self._device_change_pending = False
            self._pending_device = None
            self._last_callback_at = 0.0
            self._capture_error = None
            if self.stream:
                old_stream = self.stream
                self.stream = None
                self._release_stream_bounded(old_stream)
            self._preroll_buffer.clear()

    def get_last_audio_array(self) -> Optional[np.ndarray]:
        """Returns the last captured audio as a 1D float32 numpy array at 16kHz."""
        with self._lock:
            return getattr(self, "last_audio_array", None)
