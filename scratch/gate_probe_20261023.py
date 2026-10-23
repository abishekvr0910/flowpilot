"""Live desktop gate probe for spec 0001 AC-2, AC-3, AC-7.

Real FloatingHUD + CompanionVisibilityController + real ContextMonitor on the
interactive desktop. The fullscreen window is a separate child process so the
companion treats it as a third party app, mirroring the real spec case.

Pass criteria set before the run, per spec 0001:
  AC-2  HUD hides within one second of borderless fullscreen, and returns
        within one second of leaving it.
  AC-3  A maximized plain window must NOT be treated as fullscreen.
  AC-7  A full ContextMonitor.sample() completes in under 0.25 s.

Result: prints timings and verdict, exit code 0 only when all pass.
"""

import os
import subprocess
import sys
import time
import tempfile
from pathlib import Path

tmp = Path(tempfile.mkdtemp(prefix="fp_gate_"))
os.environ["FLOWPILOT_CONFIG_DIR"] = str(tmp)
os.environ["FLOWPILOT_MUTEX_NAME"] = "FlowPilotGateProbe"
os.environ["FLOWPILOT_HEADLESS"] = "1"
os.environ["INSIGHTS_FILE"] = str(tmp / "insights.json")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication, QWidget

from engine.companion_store import CompanionStore
from engine.preference_learning import PreferenceLearningEngine
from engine.window_inspector import ContextMonitor
from ui.companion_visibility_controller import CompanionVisibilityController
from ui.floating_hud import FloatingHUD

results = {}
failures = []


def pump_until(predicate, timeout_sec):
    app = QApplication.instance()
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_sec:
        app.processEvents()
        if predicate():
            return time.monotonic() - t0
        time.sleep(0.02)
    return None


def wait_file(path, timeout):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if path.exists():
            return True
        time.sleep(0.05)
    return False


def main():
    app = QApplication(["gate_probe"])
    store = CompanionStore(tmp)
    learning = PreferenceLearningEngine(tmp)
    store.set_visibility_mode("smart")

    monitor = ContextMonitor()
    hud = FloatingHUD()
    # The probe kitty must stay visible to Qt so AC-2 sees show/hide flips, but
    # it must never litter the user's desktop, so park it far offscreen.
    hud.move(-20000, -20000)
    controller = CompanionVisibilityController(hud, store, learning, monitor=monitor)
    controller.start()
    app.processEvents()
    hud.move(-20000, -20000)
    if controller.current.presentation == "hidden":
        failures.append("AC-2 force start on a normal desktop hid the HUD: " + controller.current.reason)

    # The probe must hold foreground when the child starts: only the foreground
    # process is allowed to hand focus off, otherwise the child claim is lost.
    probe_window = QWidget()
    probe_window.setWindowTitle("FlowPilot gate probe")
    probe_window.resize(240, 160)
    probe_window.show()
    probe_window.move(40, 40)
    probe_window.activateWindow()
    probe_window.raise_()
    try:
        import win32gui
        for _ in range(40):
            try:
                win32gui.SetForegroundWindow(probe_window.winId())
            except Exception:
                pass
            if win32gui.GetForegroundWindow() == int(probe_window.winId()):
                break
            time.sleep(0.05)
    except Exception:
        pass

    samples = []
    for _ in range(10):
        t0 = time.monotonic()
        snap = monitor.sample()
        samples.append(time.monotonic() - t0)
    results["ac7_sample_sec"] = {
        "min": f"{min(samples):.9f}", "max": f"{max(samples):.9f}",
        "avg": f"{sum(samples) / len(samples):.9f}"
    }
    if max(samples) >= 0.25:
        failures.append("AC-7 sample duration exceeded 0.25 s: " + str(max(samples)))
    if not snap.known:
        failures.append("AC-7 sample returned an unknown context on a live desktop")

    child_path = Path(__file__).resolve().parent / "ws_probe_child.py"
    child = subprocess.Popen(
        [sys.executable, "-X", "utf8", str(child_path), str(tmp)],
        cwd=str(Path(__file__).resolve().parent),
        env={**os.environ, "FLOWPILOT_HEADLESS": "0"}
    )
    try:
        if not wait_file(tmp / "child_ready", 10):
            failures.append("Child fullscreen window never came up; AC-2 unmeasurable")
        else:
            # Trust the sample, not the handshake: the child keeps re-claiming
            # foreground, so this gate usually fires within a second or two.
            gate = pump_until(lambda: monitor.sample().fullscreen, 8.0)
            results["gate_shell_state"] = monitor.sample().shell_state
            if gate is None:
                failures.append("Monitor never classified the child as fullscreen foreground; AC-2 unmeasurable")
            else:
                # AC-2 part 1: hide latency from that verified fullscreen moment.
                t0 = time.monotonic()
                lat_hide = pump_until(lambda: controller.current.presentation == "hidden", 3.0)
                results["ac2_hide_sec"] = round(lat_hide, 3) if lat_hide is not None else None
                if lat_hide is None:
                    failures.append("AC-2 companion did not hide during a borderless fullscreen child window")
                elif lat_hide > 1.0:
                    failures.append(f"AC-2 hide latency {lat_hide:.3f}s exceeded one second")
                else:
                    at_hide = monitor.sample()
                    results["at_hide_context"] = {
                        "fullscreen": at_hide.fullscreen,
                        "shell_state": at_hide.shell_state,
                        "process": at_hide.process_name,
                    }

                # AC-2 part 2: the child leaves fullscreen (bordered maximized window).
                (tmp / "child_phase2").write_text("y", encoding="utf-8")
                if wait_file(tmp / "child_phase2_done", 10):
                    lat_ret = pump_until(lambda: controller.current.presentation != "hidden" and hud.isVisible(), 3.0)
                    results["ac2_restore_sec"] = round(lat_ret, 3) if lat_ret is not None else None
                    if lat_ret is None:
                        failures.append("AC-2 companion never returned after leaving fullscreen")
                    elif lat_ret > 1.0:
                        failures.append(f"AC-2 restore latency {lat_ret:.3f}s exceeded one second")
                else:
                    failures.append("Child never left fullscreen; restore latency unmeasurable")

                # AC-3 stability: a maximized bordered window must hold the companion.
                hold = pump_until(lambda: controller.current.presentation == "hidden", 1.2)
                if hold is not None:
                    failures.append("AC-3 companion dropped on a bordered maximized window")
                if not hud.isVisible():
                    failures.append("AC-3 companion lost visibility while a plain window was maximized")
    finally:
        probe_window.close()
        (tmp / "child_close").write_text("y", encoding="utf-8")
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill()
        controller.stop()
        controller.hud.hide()
        app.processEvents()

    print("== Interactive gate probe results ==")
    for key, value in results.items():
        print(f"{key}: {value}")
    if failures:
        print("VERDICT: FAILED")
        for f in failures:
            print("  -", f)
        raise SystemExit(1)
    print("VERDICT: PASSED")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
