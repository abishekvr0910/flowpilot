"""
FlowPilot Native Desktop Application
Native Windows desktop app with:
- Win32 RegisterHotKey global shortcuts (Ctrl+Shift+Space / F9)
- Floating microphone HUD (Flow Pill with WS_EX_NOACTIVATE)
- System Tray integration and notifications
- Real-time local Whisper speech recognition
- Context-aware background audio ducking & text injection
"""

import sys
import os
import signal
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal, Qt

from engine import __version__
from engine.single_instance import SingleInstance
from engine.orchestrator import FlowOrchestrator
from engine.config import load_config, save_config
from ui.floating_hud import FloatingHUD
from ui.tray_manager import TrayManager
from ui.settings_dialog import SettingsDialog

class StateBridge(QObject):
    state_changed = Signal(dict)

class FlowPilotApp:
    def __init__(self, enforce_single_instance: bool = True):
        # 0. Enforce single instance
        self.single_instance = SingleInstance() if enforce_single_instance else None
        if self.single_instance and self.single_instance.is_already_running():
            print("[FlowPilot] Another instance of FlowPilot is already running.")
            if sys.platform == "win32" and not os.environ.get("FLOWPILOT_NO_POPUP") and not os.environ.get("CI") and "FLOWPILOT_MUTEX_NAME" not in os.environ:
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    if hasattr(user32, "MessageBoxTimeoutW"):
                        user32.MessageBoxTimeoutW(
                            0,
                            "FlowPilot is already running!\n\nLook for the companion on your screen or the FlowPilot icon in your System Tray (near the clock).\n\nPress Ctrl+Shift+Space or hold F9 anytime to dictate.",
                            "FlowPilot Voice Intelligence",
                            0x40,  # MB_ICONINFORMATION
                            0,
                            2500   # Auto-dismiss after 2.5 seconds to prevent modal hang
                        )
                    else:
                        print("[FlowPilot Warning] FlowPilot is already running.")
                except Exception:
                    pass
            sys.exit(0)

        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName("FlowPilot")
        self.app.setApplicationDisplayName("FlowPilot Voice Intelligence")
        self.app.setApplicationVersion(__version__)
        self.app.setQuitOnLastWindowClosed(False)

        self.bridge = StateBridge()
        self.config = load_config()

        # 1. Initialize Core Engine Orchestrator
        self.orchestrator = FlowOrchestrator(on_state_change=self._on_engine_state_change)

        # 1b. Warm up audio capture stream for zero-latency pre-roll
        try:
            self.orchestrator.recorder.warmup_stream()
        except Exception as e:
            print(f"[FlowPilot Warning] Audio pre-roll warmup deferred: {e}")

        # 2. Initialize UI Components
        self.hud = FloatingHUD()
        self.tray = TrayManager()
        self.settings_dlg = None

        hk_str = self.config.get("hotkey", "Ctrl+Shift+Space")
        hk_mode = self.config.get("hotkey_mode", "toggle")
        self.hud.set_hotkey_info(hk_str, hk_mode)
        self.tray.set_hotkey_info(hk_str, hk_mode)

        # 3. Connect UI Signals
        self.bridge.state_changed.connect(self._handle_state_update)

        # Unified dictation triggers: Floating HUD button & Tray click & Hotkeys
        self.hud.toggle_requested.connect(self.orchestrator.toggle_dictation)
        self.tray.toggle_requested.connect(self.orchestrator.toggle_dictation)

        # Emergency cancel triggers
        self.hud.cancel_requested.connect(self.orchestrator.cancel_dictation)
        self.tray.cancel_requested.connect(self.orchestrator.cancel_dictation)

        # Recovery triggers
        self.hud.recopy_requested.connect(self._on_recopy_last)
        self.tray.recopy_requested.connect(self._on_recopy_last)

        self.hud.settings_requested.connect(self.show_settings)
        self.tray.settings_requested.connect(self.show_settings)

        self.tray.toggle_hud_requested.connect(self.toggle_hud_visibility)
        self.tray.switch_visual_requested.connect(self.hud.toggle_visual_style)
        self.tray.ducking_toggled.connect(self._on_ducking_toggled)

        self.hud.quit_requested.connect(self.quit)
        self.tray.quit_requested.connect(self.quit)

        # 4. Position Floating Robot Mascot Companion (Restore saved position or default to bottom right)
        screen = self.app.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            saved_x = self.config.get("hud_x")
            saved_y = self.config.get("hud_y")
            if saved_x is not None and saved_y is not None and saved_x > 20 and saved_y > 20:
                x = max(geom.left() + 20, min(saved_x, geom.right() - self.hud.width() - 20))
                y = max(geom.top() + 20, min(saved_y, geom.bottom() - self.hud.height() - 20))
                self.hud.move(x, y)
            else:
                x = geom.right() - self.hud.width() - 24
                y = geom.bottom() - self.hud.height() - 24
                self.hud.move(x, y)
        self.hud.show()
        self.hud.raise_()

        # 5. Start Global Win32 Hotkey Service
        self.orchestrator.start_hotkey_listener()
        print("\n============================================================")
        print("   FLOWPILOT NATIVE DESKTOP APPLICATION ACTIVE")
        print("============================================================")
        print("[*] Global Shortcuts: 'Ctrl + Shift + Space', 'Ctrl + Alt + Space', 'F9'")
        print("[*] Robot Companion:  Pilot Active (Draggable to any corner)")
        print("[*] System Tray:      Active")
        print("============================================================\n")

    def _on_engine_state_change(self, payload: dict):
        # Dispatches thread-safe from engine worker threads into Qt GUI thread
        self.bridge.state_changed.emit(payload)

    def _handle_state_update(self, payload: dict):
        state = payload.get("state", "idle")
        self.hud.update_state(state, payload)
        self.tray.set_state(state)

        if state == "error":
            err = payload.get("message", "Unknown error")
            self.tray.show_notification("FlowPilot Error", err, is_error=True)

    def toggle_hud_visibility(self):
        if self.hud.isVisible():
            self.hud.hide()
        else:
            self.hud.show()

    def _on_ducking_toggled(self, enabled: bool):
        self.orchestrator.ducker.duck_mode = "mute" if enabled else "off"
        print(f"[FlowPilot] Audio ducking mode set to: {self.orchestrator.ducker.duck_mode}")

    def show_settings(self):
        if not self.settings_dlg:
            self.settings_dlg = SettingsDialog(
                self.orchestrator.config,
                self._on_save_settings,
                personalization=self.orchestrator.personalization
            )
        self.settings_dlg.show()
        self.settings_dlg.raise_()
        self.settings_dlg.activateWindow()

    def _on_save_settings(self, new_config: dict):
        self.orchestrator.update_config(new_config)
        hk_str = self.orchestrator.config.get("hotkey", "Ctrl+Shift+Space")
        hk_mode = self.orchestrator.config.get("hotkey_mode", "toggle")
        self.hud.set_hotkey_info(hk_str, hk_mode)
        self.tray.set_hotkey_info(hk_str, hk_mode)

    def _on_recopy_last(self):
        success = self.orchestrator.re_copy_last()
        if success:
            self.tray.show_notification("FlowPilot", "Last dictation copied to clipboard!")
        else:
            self.tray.show_notification("FlowPilot", "No previous dictation found to copy.")

    def quit(self):
        print("[FlowPilot] Shutting down cleanly...")
        self.orchestrator.stop_hotkey_listener()
        try:
            self.orchestrator.ducker.stop_ducking()
        except Exception:
            pass
        try:
            self.orchestrator.recorder.close()
        except Exception:
            pass
        if hasattr(self, 'single_instance') and self.single_instance:
            self.single_instance.release()
        self.hud.close()
        self.app.quit()

    def run(self):
        return self.app.exec()

def main():
    # Handle Ctrl+C in terminal cleanly
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = FlowPilotApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()
