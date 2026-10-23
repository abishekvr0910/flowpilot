"""Child fullscreen window for the live gate probe. Separate process so the
companion treats it as a third party app, which is the real spec 0001 case."""

import os
import sys
import time
from pathlib import Path

state_dir = Path(sys.argv[1])

os.environ.setdefault("QT_QPA_PLATFORM", "")
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QWidget

app = QApplication([])
window = QWidget()
window.setWindowFlags(Qt.FramelessWindowHint)
window.setStyleSheet("background-color: #202024; color: #9a9aa0;")
(window_state := {"claimed": False})

import win32gui

def claim():
    try:
        win32gui.SetForegroundWindow(window.winId())
    except Exception:
        pass
    try:
        if win32gui.GetForegroundWindow() == int(window.winId()):
            window_state["claimed"] = True
    except Exception:
        pass

def present():
    window.showFullScreen()
    window.raise_()
    claim()
    (state_dir / "child_ready").write_text("y", encoding="utf-8")

QTimer.singleShot(80, present)

deadline = time.monotonic() + 40
while time.monotonic() < deadline:
    app.processEvents()
    if (state_dir / "child_phase2").exists():
        window.showMaximized()
        window.setWindowFlags(Qt.Window)
        window.showMaximized()
        (state_dir / "child_phase2_done").write_text("y", encoding="utf-8")
        (state_dir / "child_phase2").unlink(missing_ok=True)
    elif not window_state["claimed"] and not (state_dir / "child_phase2").exists():
        claim()
        if window_state["claimed"]:
            (state_dir / "child_claimed").write_text("y", encoding="utf-8")
    if (state_dir / "child_close").exists():
        break
    time.sleep(0.05)
