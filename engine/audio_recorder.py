import io
import time
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
from typing import Callable, Optional

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
        self._lock = threading.Lock()

    def _audio_callback(self, indata, frames, time_info, status):
        if not self.is_recording:
            return
        try:
            if status:
                print(f"[Audio Warning] {status}")
            self.audio_frames.append(indata.copy())
            if self.level_callback:
                rms = np.sqrt(np.mean(indata**2))
                level = min(1.0, float(rms * 10.0))
                self.level_callback(level)
        except Exception:
            pass

    def start_recording(self):
        with self._lock:
            if self.is_recording:
                return
            if self.sample_rate <= 0:
                raise ValueError(f"Invalid sample rate: {self.sample_rate}")

            # Ensure any lingering stream is cleanly terminated
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None

            self.audio_frames = []
            self.last_audio_array = None
            self.capture_sample_rate = self.sample_rate
            self.is_recording = True

            try:
                # First attempt: Target sample rate (16000Hz)
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="float32",
                    device=self.device,
                    callback=self._audio_callback
                )
                self.stream.start()
                print("[Audio] Recording started...")
            except Exception as e:
                # Fallback attempt: If hardware requires 44.1kHz or 48kHz, query native rate
                fallback_success = False
                try:
                    dev_info = sd.query_devices(self.device, "input")
                    native_sr = int(dev_info.get("default_samplerate", 44100))
                    if native_sr != self.sample_rate and native_sr > 0:
                        print(f"[Audio] Target sample rate {self.sample_rate}Hz rejected. Falling back to native {native_sr}Hz with dynamic resampling.")
                        self.capture_sample_rate = native_sr
                        self.stream = sd.InputStream(
                            samplerate=native_sr,
                            channels=self.channels,
                            dtype="float32",
                            device=self.device,
                            callback=self._audio_callback
                        )
                        self.stream.start()
                        fallback_success = True
                        print("[Audio] Recording started with native hardware sample rate fallback.")
                except Exception:
                    pass

                if not fallback_success:
                    self.is_recording = False
                    print(f"[Audio Error] Failed to start stream: {e}")
                    raise e

    def stop_recording(self) -> Optional[bytes]:
        with self._lock:
            if not self.is_recording and not self.stream:
                return None
            self.is_recording = False
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None

            if not self.audio_frames:
                print("[Audio] No audio frames captured.")
                self.last_audio_array = None
                return None

            # Concatenate frames
            recording = np.concatenate(self.audio_frames, axis=0)
            self.audio_frames = []
            
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

    def get_last_audio_array(self) -> Optional[np.ndarray]:
        """Returns the last captured audio as a 1D float32 numpy array at 16kHz."""
        with self._lock:
            return getattr(self, "last_audio_array", None)
