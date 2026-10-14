import sys
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

    def start_ducking(self):
        if not HAS_PYCAW or sys.platform != "win32" or self.is_ducked:
            return

        try:
            import comtypes
            comtypes.CoInitialize()
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

    def stop_ducking(self):
        if not HAS_PYCAW or not self.is_ducked:
            return

        try:
            import comtypes
            comtypes.CoInitialize()
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
