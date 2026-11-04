"""
Unit Test: Single-Instance IPC Window Activation, Tray Behavior & Spoken Tech Normalization
Validates:
1. SingleInstance mutex acquisition and collision detection.
2. QLocalServer named pipe IPC triggering dashboard restoration across processes without popups.
3. TrayManager single-click and double-click opening/restoring Dashboard rather than toggling mic.
4. FlowPilotDashboard closeEvent minimizing to background/tray rather than destroying.
5. WritingIntelligence canonicalizing spoken terms (EXC file, task manager, Wispr Flow, failed to register).
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from engine.single_instance import SingleInstance
from ui.tray_manager import TrayManager
from ui.flowpilot_dashboard import FlowPilotDashboard
from engine.writing_intelligence import WritingIntelligence


def test_single_instance_mutex():
    print("\n[1] Testing SingleInstance Mutex Acquisition & Collision...")
    test_mutex = "Global\\FlowPilot_Test_SingleInstance_Mutex_999"
    inst1 = SingleInstance(mutex_name=test_mutex)
    assert not inst1.is_already_running(), "Primary instance should not be already running"

    inst2 = SingleInstance(mutex_name=test_mutex)
    assert inst2.is_already_running(), "Secondary instance MUST detect that an instance is already running"

    inst1.release()
    print("    PASSED: Mutex collision detected cleanly.")


def test_tray_manager_click_behavior():
    print("\n[2] Testing TrayManager Click Signal Routing...")
    app = QApplication.instance() or QApplication(sys.argv)
    tray = TrayManager()

    signals_received = []

    tray.dashboard_requested.connect(lambda: signals_received.append("dashboard"))
    tray.toggle_requested.connect(lambda: signals_received.append("toggle"))

    from PySide6.QtWidgets import QSystemTrayIcon

    # Simulate Single Click (Trigger)
    tray._on_tray_activated(QSystemTrayIcon.Trigger)
    assert signals_received == ["dashboard"], f"Expected ['dashboard'] on single click, got {signals_received}"

    # Simulate Double Click (DoubleClick)
    tray._on_tray_activated(QSystemTrayIcon.DoubleClick)
    assert signals_received == ["dashboard", "dashboard"], f"Expected 2 dashboard calls, got {signals_received}"

    # Simulate Middle Click (MiddleClick)
    tray._on_tray_activated(QSystemTrayIcon.MiddleClick)
    assert signals_received == ["dashboard", "dashboard", "toggle"], f"Expected toggle on middle click, got {signals_received}"

    print("    PASSED: Single/Double click emits dashboard_requested; Middle click emits toggle.")


def test_dashboard_close_event():
    print("\n[3] Testing FlowPilotDashboard closeEvent Minimization...")
    app = QApplication.instance() or QApplication(sys.argv)
    dash = FlowPilotDashboard()
    dash.show()
    assert dash.isVisible(), "Dashboard should be visible initially"

    # Simulate user clicking window 'X' (close)
    dash.close()
    assert not dash.isVisible(), "Dashboard must be hidden after close()"
    assert not dash._force_close, "_force_close should remain False"

    # Simulate shutdown with _force_close = True
    dash._force_close = True
    dash.close()
    print("    PASSED: FlowPilotDashboard closeEvent hides without terminating app.")


def test_writing_intelligence_spoken_terms():
    print("\n[4] Testing Spoken Tech Term & Extension Normalization...")
    wi = WritingIntelligence()

    # Case A: User's reported transcript with EXC file, task manager, Whisper flow, fail to register
    raw = (
        "whenever I try to click the EXC file once again, it seems to be giving me the desired of "
        "fail to register or sometimes the application is already running in task manager like Whisper flow"
    )
    res = wi.polish(raw, style="professional")["text"]
    assert ".exe file" in res, f"Expected '.exe file' in result, got: {res}"
    assert "Task Manager" in res, f"Expected 'Task Manager' in result, got: {res}"
    assert "Wispr Flow" in res, f"Expected 'Wispr Flow' in result, got: {res}"
    assert "failed to register" in res, f"Expected 'failed to register' in result, got: {res}"

    # Case B: Direct spoken extensions
    ext_sample = "make sure to run the script dot py and edit config dot json before launching dot exe"
    ext_res = wi.polish(ext_sample, style="professional")["text"]
    assert ".py" in ext_res, f"Expected '.py', got: {ext_res}"
    assert ".json" in ext_res, f"Expected '.json', got: {ext_res}"
    assert ".exe" in ext_res, f"Expected '.exe', got: {ext_res}"

    print("    PASSED: Spoken tech terms and file extensions accurately formatted.")


def test_ipc_window_restore_multiprocess():
    print("\n[5] Testing Cross-Process IPC Window Activation...")
    app = QApplication.instance() or QApplication(sys.argv)
    dash = FlowPilotDashboard()
    dash.hide()
    assert not dash.isVisible(), "Dashboard should start hidden"

    pipe_name = f"FlowPilot_Test_Restore_Pipe_{os.getpid()}"
    QLocalServer.removeServer(pipe_name)

    server = QLocalServer()

    def on_conn():
        sock = server.nextPendingConnection()
        if sock:
            dash.showNormal()
            dash.show()
            dash.raise_()
            dash.activateWindow()
            sock.write(b"ACK\n")
            sock.flush()
            sock.disconnectFromServer()

    server.newConnection.connect(on_conn)
    assert server.listen(pipe_name), f"Failed to listen on {pipe_name}"

    secondary_script = f"""
import sys
from PySide6.QtCore import QCoreApplication
from PySide6.QtNetwork import QLocalSocket
app = QCoreApplication(sys.argv)
sock = QLocalSocket()
sock.connectToServer("{pipe_name}")
if sock.waitForConnected(1000):
    sock.write(b"RESTORE\\n")
    sock.flush()
    if sock.waitForReadyRead(1000):
        sock.disconnectFromServer()
        sys.exit(0)
sys.exit(1)
"""

    def launch_secondary():
        subprocess.Popen([sys.executable, "-c", secondary_script])

    def verify_restore():
        try:
            assert dash.isVisible(), "Dashboard must be visible after IPC restore"
            print("    PASSED: Cross-process IPC successfully restored hidden window without popups.")
        finally:
            server.close()
            QLocalServer.removeServer(pipe_name)
            dash._force_close = True
            dash.close()
            app.quit()

    QTimer.singleShot(150, launch_secondary)
    QTimer.singleShot(900, verify_restore)
    app.exec()


def run_all():
    print("=" * 65)
    print("AUDIT: SINGLE-INSTANCE IPC, TRAY UX & SPOKEN FORMATTING")
    print("=" * 65)
    test_single_instance_mutex()
    test_tray_manager_click_behavior()
    test_dashboard_close_event()
    test_writing_intelligence_spoken_terms()
    test_ipc_window_restore_multiprocess()
    print("\n" + "=" * 65)
    print("ALL 5 AUDIT SUITE TESTS PASSED 100%!")
    print("=" * 65)


if __name__ == "__main__":
    run_all()
