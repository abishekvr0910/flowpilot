"""
FlowPilot Audio Feedback Engine
Plays distinct audio chimes using Windows winsound.Beep in background threads.
Provides instant sensory confirmation for Start, Stop, Cancel, and Error states.
"""

import sys
import threading
import time

class AudioFeedback:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def _play(self, tones):
        if not self.enabled or sys.platform != "win32":
            return
        def worker():
            try:
                import winsound
                for freq, dur in tones:
                    winsound.Beep(freq, dur)
                    time.sleep(0.02)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True, name="FlowPilot-AudioFeedback").start()

    def play_start(self):
        # Ascending two-tone chime: 880Hz -> 1320Hz (A5 -> E6)
        self._play([(880, 70), (1320, 90)])

    def play_stop(self):
        # Descending two-tone chime: 1320Hz -> 880Hz (E6 -> A5)
        self._play([(1320, 70), (880, 90)])

    def play_cancel(self):
        # Double low pulse: 440Hz -> 330Hz
        self._play([(440, 90), (330, 110)])

    def play_error(self):
        # Low buzz: 220Hz
        self._play([(220, 180)])
