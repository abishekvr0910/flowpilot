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
        self._lock = threading.Lock()

    def _play(self, tones):
        if not self.enabled or sys.platform != "win32":
            return
        def worker():
            if not self._lock.acquire(blocking=False):
                return
            try:
                import winsound
                for freq, dur in tones:
                    winsound.Beep(freq, dur)
                    time.sleep(0.02)
            except Exception:
                pass
            finally:
                self._lock.release()
        threading.Thread(target=worker, daemon=True, name="FlowPilot-AudioFeedback").start()

    def play_start(self):
        # Soft ascending chime: 587Hz -> 880Hz (D5 -> A5)
        self._play([(587, 45), (880, 50)])

    def play_stop(self):
        # Soft descending chime: 880Hz -> 587Hz (A5 -> D5)
        self._play([(880, 45), (587, 50)])

    def play_cancel(self):
        # Soft low pulse: 440Hz -> 349Hz
        self._play([(440, 45), (349, 55)])

    def play_error(self):
        # Low buzz: 220Hz
        self._play([(220, 180)])
