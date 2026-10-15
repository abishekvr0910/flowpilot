import sys
import threading
from typing import Optional

try:
    from pycaw.pycaw import AudioUtilities
    HAS_PYCAW = True
except ImportError:
    HAS_PYCAW = False

class AudioDucker:
    """
    Automatically silences/ducks background media (e.g. YouTube, Spotify)
    while dictating so the microphone captures pure voice without bleed.
    Restores original volume immediately upon release.
    """
    def __init__(self, duck_mode: str = "mute"):
        self.duck_mode = duck_mode  # "mute" or "duck" (lower to 10%)
        self.original_mute: Optional[bool] = None
        self.original_volume: Optional[float] = None
        self.is_ducked = False
        self._lock = threading.Lock()

    def start_ducking(self):
        with self._lock:
            if self.is_ducked:
                return

            if HAS_PYCAW and sys.platform == "win32":
                co_init = False
                try:
                    import comtypes
                    comtypes.CoInitialize()
                    co_init = True
                except Exception:
                    pass

                try:
                    speakers = AudioUtilities.GetSpeakers()
                    if not speakers:
                        return
                    volume_endpoint = speakers.EndpointVolume
                    if not volume_endpoint:
                        return

                    self.original_mute = bool(volume_endpoint.GetMute())
                    self.original_volume = float(volume_endpoint.GetMasterVolumeLevelScalar())

                    if self.duck_mode == "mute":
                        volume_endpoint.SetMute(1, None)
                    else:
                        # Lower to 10% volume
                        volume_endpoint.SetMasterVolumeLevelScalar(min(self.original_volume, 0.1), None)

                    self.is_ducked = True
                    print(f"[AudioDucker] Background audio silenced (original vol: {int(self.original_volume * 100)}%).")
                except Exception as e:
                    print(f"[AudioDucker Warning] Could not silence background audio: {e}")
                finally:
                    if co_init:
                        try:
                            import comtypes
                            comtypes.CoUninitialize()
                        except Exception:
                            pass
            elif sys.platform.startswith("linux"):
                try:
                    import subprocess
                    res = subprocess.run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"], capture_output=True, text=True, timeout=0.1)
                    if res.returncode == 0:
                        self.original_mute = "yes" in res.stdout.lower()
                        subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"], check=False, timeout=0.1)
                        self.is_ducked = True
                        print("[AudioDucker] Background audio muted via pactl (Linux).")
                except Exception:
                    pass
            elif sys.platform == "darwin":
                try:
                    import subprocess
                    res = subprocess.run(["osascript", "-e", "output muted of (get volume settings)"], capture_output=True, text=True, timeout=0.1)
                    if res.returncode == 0:
                        self.original_mute = "true" in res.stdout.lower()
                        subprocess.run(["osascript", "-e", "set volume with output muted"], check=False, timeout=0.1)
                        self.is_ducked = True
                        print("[AudioDucker] Background audio muted via osascript (macOS).")
                except Exception:
                    pass

    def stop_ducking(self):
        with self._lock:
            if not self.is_ducked:
                return

            if HAS_PYCAW and sys.platform == "win32":
                co_init = False
                try:
                    import comtypes
                    comtypes.CoInitialize()
                    co_init = True
                except Exception:
                    pass

                try:
                    speakers = AudioUtilities.GetSpeakers()
                    if speakers and speakers.EndpointVolume:
                        vol = speakers.EndpointVolume
                        if self.original_mute is not None:
                            vol.SetMute(int(self.original_mute), None)
                        if self.original_volume is not None:
                            vol.SetMasterVolumeLevelScalar(self.original_volume, None)

                    print("[AudioDucker] Background audio restored.")
                except Exception as e:
                    print(f"[AudioDucker Warning] Could not restore audio: {e}")
                finally:
                    self.is_ducked = False
                    self.original_mute = None
                    self.original_volume = None
                    if co_init:
                        try:
                            import comtypes
                            comtypes.CoUninitialize()
                        except Exception:
                            pass
            elif sys.platform.startswith("linux"):
                try:
                    import subprocess
                    if self.original_mute is False:
                        subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"], check=False, timeout=0.1)
                    print("[AudioDucker] Background audio restored via pactl (Linux).")
                except Exception:
                    pass
                finally:
                    self.is_ducked = False
                    self.original_mute = None
            elif sys.platform == "darwin":
                try:
                    import subprocess
                    if self.original_mute is False:
                        subprocess.run(["osascript", "-e", "set volume without output muted"], check=False, timeout=0.1)
                    print("[AudioDucker] Background audio restored via osascript (macOS).")
                except Exception:
                    pass
                finally:
                    self.is_ducked = False
                    self.original_mute = None
