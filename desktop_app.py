"""
Feature 32: FlowPilot Native Desktop Application
Native Windows desktop app with:
- Win32 RegisterHotKey global shortcuts (user-selected dictation key)
- Floating microphone HUD (Flow Pill with WS_EX_NOACTIVATE)
- System Tray integration and notifications
- Real-time local Whisper speech recognition
- Context-aware background audio ducking & text injection
"""

import sys
import os
import signal
import threading
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
from ui.companion_studio import CompanionStudioDialog
from ui.flowpilot_dashboard import FlowPilotDashboard
from ui.setup_wizard import SetupWizardDialog
from ui.companion_visibility_controller import CompanionVisibilityController
from engine.companion_store import get_companion_store
from engine.media_presence import SampledMediaPresence
from engine.preference_learning import get_learning_engine

class StateBridge(QObject):
    state_changed = Signal(dict)

class FlowPilotApp:
    def __init__(self, enforce_single_instance: bool = True):
        # 0. Enforce single instance
        self.single_instance = SingleInstance() if enforce_single_instance else None
        if self.single_instance and self.single_instance.is_already_running():
            print("[FlowPilot] Another instance of FlowPilot is already running. Bringing window to front.")
            if sys.platform == "win32":
                try:
                    import win32gui
                    import win32con
                    hwnd = win32gui.FindWindowW(None, "FlowPilot")
                    if not hwnd:
                        hwnd = win32gui.FindWindowW(None, "FlowPilot - Voice Intelligence Dashboard")
                    if hwnd:
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    pass
            if sys.platform == "win32" and not os.environ.get("FLOWPILOT_NO_POPUP") and not os.environ.get("CI") and "FLOWPILOT_MUTEX_NAME" not in os.environ:
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    if hasattr(user32, "MessageBoxTimeoutW"):
                        user32.MessageBoxTimeoutW(
                            0,
                            "FlowPilot is already running!\n\nLook for the companion on your screen or the FlowPilot icon in your System Tray (near the clock).\n\nUse your configured dictation shortcut to speak.",
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

        # Application-wide wheel guard: scrolling over closed dropdowns or unfocused sliders
        # never accidentally changes settings; scroll events are cleanly forwarded to the page.
        from ui.flowpilot_dashboard import _ensure_wheel_guard
        _ensure_wheel_guard(self.app)

        self.bridge = StateBridge()
        self.config = load_config()

        # 1. Initialize Core Engine Orchestrator
        self.orchestrator = FlowOrchestrator(on_state_change=self._on_engine_state_change)

        # 1b. Warm up audio capture without blocking the Qt startup on a USB driver.
        def warmup_microphone():
            try:
                self.orchestrator.recorder.warmup_stream()
            except Exception as exc:
                print(f"[FlowPilot Warning] Audio pre-roll warmup deferred: {exc}")

        threading.Thread(target=warmup_microphone, daemon=True, name="FlowPilot-MicWarmup").start()

        # 2. Initialize UI Components
        self.hud = FloatingHUD()
        self.tray = TrayManager()
        self.dashboard = FlowPilotDashboard(
            config=self.config,
            on_save_config=self._on_save_settings,
            on_dictate=self.orchestrator.toggle_dictation,
            personalization=self.orchestrator.personalization
        )
        self.visibility = CompanionVisibilityController(
            self.hud, get_companion_store(), get_learning_engine(),
            media=SampledMediaPresence(),
        )
        self.visibility.decision_changed.connect(self._on_visibility_changed)
        self.visibility.error.connect(self._on_visibility_error)
        self.settings_dlg = None
        self.studio_dlg = None

        hk_str = self.config.get("hotkey", "Ctrl+Shift+Space")
        hk_mode = self.config.get("hotkey_mode", "toggle")
        self.hud.set_hotkey_info(hk_str, hk_mode)
        self.tray.set_hotkey_info(hk_str, hk_mode)
        cur_lang = self.config.get("language", "auto")
        is_trans = self.config.get("translate_to_english", False)
        self.tray.set_language_info(cur_lang, is_trans)

        # 3. Connect UI Signals
        self.bridge.state_changed.connect(self._handle_state_update)
        self.bridge.state_changed.connect(self.visibility.set_state_hint)

        # Dashboard triggers
        self.hud.dashboard_requested.connect(self.show_dashboard)
        self.tray.dashboard_requested.connect(self.show_dashboard)
        self.dashboard.companion_changed.connect(self._on_companion_switched_from_dashboard)
        self.dashboard.companion_settings_applied.connect(self._on_companion_applied)
        self.dashboard.show_companion_requested.connect(self.visibility.show_now)
        self.dashboard.companion_visibility_requested.connect(self.visibility.set_mode)
        self.dashboard.dictate_requested.connect(self.orchestrator.toggle_dictation)

        # Unified dictation triggers: Floating HUD button & Tray click & Hotkeys
        self.hud.toggle_requested.connect(self.orchestrator.toggle_dictation)
        self.tray.toggle_requested.connect(self.orchestrator.toggle_dictation)

        # Emergency cancel triggers
        self.hud.cancel_requested.connect(self.orchestrator.cancel_dictation)
        self.tray.cancel_requested.connect(self.orchestrator.cancel_dictation)

        # Recovery triggers (matching Wispr Shift+Alt+Z / Shift+Alt+X)
        self.hud.recopy_requested.connect(self._on_recopy_last)
        self.tray.recopy_requested.connect(self._on_recopy_last)
        self.tray.reinject_requested.connect(self._on_reinject_last)

        self.hud.settings_requested.connect(self.show_settings)
        self.tray.settings_requested.connect(self.show_settings)

        # Language and Translation triggers
        self.tray.language_changed.connect(self._on_tray_language_changed)
        self.tray.translate_toggled.connect(self._on_tray_translate_toggled)

        # Companion Studio triggers
        self.hud.studio_requested.connect(self.show_companion_studio)
        self.tray.studio_requested.connect(self.show_companion_studio)
        self.tray.restore_hud_requested.connect(self.restore_hud)

        self.tray.toggle_hud_requested.connect(self.toggle_hud_visibility)
        self.tray.show_now_requested.connect(self.visibility.show_now)
        self.tray.visibility_mode_requested.connect(self.visibility.set_mode)
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
                y = geom.bottom() - self.hud.height() - 140
                self.hud.move(x, y)
        self.visibility.start()

        # Show setup wizard on first run, or master application dashboard window
        if enforce_single_instance and not os.environ.get("CI") and not os.environ.get("FLOWPILOT_HEADLESS"):
            if not self.config.get("first_run_completed", False):
                self.show_setup_wizard()
            else:
                self.show_dashboard()

        # 4b. Keep transforms bound when the dictation shortcut is changed live.
        try:
            self.orchestrator.add_auxiliary_hotkey("Ctrl+Alt+T", self._on_transforms_hotkey)
        except Exception as _e:
            print(f"[FlowPilot Warning] Transforms hotkey registration deferred: {_e}")

        # 5. Start Global Win32 Hotkey Service
        self.orchestrator.start_hotkey_listener()
        print("\n============================================================")
        print("   FLOWPILOT NATIVE DESKTOP APPLICATION ACTIVE")
        print("============================================================")
        print(f"[*] Dictation shortcut: '{hk_str}' ({hk_mode}); transforms: 'Ctrl + Alt + T'")
        if not self.config.get("hotkey_exclusive", False):
            print("[*] Legacy dictation aliases remain active until you choose a shortcut in Settings: F9, Ctrl + Alt + Space")
        print("[*] Robot Companion:  Pilot Active (Draggable to any corner)")
        print("[*] System Tray:      Active")
        print("============================================================\n")

    def _on_engine_state_change(self, payload: dict):
        # Dispatches thread-safe from engine worker threads into Qt GUI thread
        self.bridge.state_changed.emit(payload)

    def _handle_state_update(self, payload: dict):
        state = payload.get("state", "idle")
        confirmed = payload.get("injection_confirmed", True)
        notice = payload.get("notice")

        # When injection into destination window could not be physically verified
        # Truthful status is updated on HUD and tray tooltip; do not fire intrusive OS warning toast
        if state in ("pasted", "success") and not confirmed:
            state = "unverified"
            payload["state"] = "unverified"

        self.hud.update_state(state, payload)
        self.tray.set_state(state)

        # Sync with dashboard components
        if hasattr(self, 'dashboard') and self.dashboard:
            is_recording = state in ("listening", "recording")
            self.dashboard.scratchpad_view.set_recording_state(is_recording)
            if state in ("pasted", "success") and not payload.get("recovery_action", False):
                fmt_text = payload.get("text") or payload.get("formatted_text")
                if fmt_text:
                    if self.dashboard.scratchpad_view.editor.hasFocus():
                        self.dashboard.scratchpad_view.insert_text(fmt_text)
                    if self.dashboard.notetaker_view.engine.is_recording:
                        self.dashboard.notetaker_view.append_segment(fmt_text)
                    if hasattr(self.dashboard, 'history_view'):
                        self.dashboard.history_view.reload_history()

        if state == "error":
            err = payload.get("message", "Unknown error")
            self.tray.show_notification("FlowPilot Error", err, is_error=True)

    def _on_transforms_hotkey(self):
        try:
            from engine.transforms_engine import get_transforms_engine
            sel_text = get_transforms_engine().get_selected_text_from_active_window()
            if hasattr(self, 'dashboard') and self.dashboard:
                self.dashboard.open_transforms(sel_text)
        except Exception as _e:
            print(f"[FlowPilot Warning] Transforms hotkey handling: {_e}")

    def show_dashboard(self):
        if hasattr(self, 'dashboard') and self.dashboard:
            self.dashboard.showNormal()
            self.dashboard.show()
            self.dashboard.raise_()
            self.dashboard.activateWindow()

    def show_setup_wizard(self):
        if not hasattr(self, 'wizard_dlg') or not self.wizard_dlg:
            self.wizard_dlg = SetupWizardDialog(self.dashboard, config=self.config)
            self.wizard_dlg.setup_completed.connect(self._on_save_settings)
            self.wizard_dlg.setup_completed.connect(self.show_dashboard)
        self.wizard_dlg.show()
        self.wizard_dlg.raise_()
        self.wizard_dlg.activateWindow()

    def _on_companion_switched_from_dashboard(self, asset_id: str):
        self.hud.set_visual_style(asset_id)
        if asset_id == "kitty":
            self.hud._cat_palette = "orange tabby"
        elif asset_id == "dog":
            self.hud._cat_palette = "shiba inu"
        elif asset_id in ("fox", "dino", "ghost", "bunny", "pikachu", "charmander", "gengar", "eevee"):
            self.hud._cat_palette = asset_id
        self.hud._cat_pixmap_cache.clear()
        self.hud.update()

    def toggle_hud_visibility(self):
        self.visibility.toggle()

    def restore_hud(self):
        if self.visibility.store.get("visibility_mode") == "hidden":
            self.visibility.set_mode(self.visibility.store.get("last_visible_mode", "smart"))
        self.visibility.show_now()
        self.hud.set_presentation("normal")
        self.hud.snap_to_corner("bottom_right")
        self.visibility.refresh(force=True)

    def _on_visibility_changed(self, presentation: str, reason: str):
        mode = self.visibility.store.get("visibility_mode", "smart")
        self.tray.set_visibility_status(mode, presentation, reason)
        self.dashboard.home_page.set_visibility_status(presentation, reason)

    def _on_visibility_error(self, message: str):
        self.tray.show_notification("Companion setting not saved", message, is_error=True)
        self.dashboard.home_page.refresh()

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
        if not self.orchestrator.update_config(new_config):
            return False
        self.config = new_config
        if hasattr(self, "dashboard"):
            self.dashboard.config = dict(new_config)
            self.dashboard.home_page.refresh()
        hk_str = self.orchestrator.config.get("hotkey", "Ctrl+Shift+Space")
        hk_mode = self.orchestrator.config.get("hotkey_mode", "toggle")
        self.hud.set_hotkey_info(hk_str, hk_mode)
        self.tray.set_hotkey_info(hk_str, hk_mode)
        self.tray.set_language_info(
            self.config.get("language", "auto"),
            self.config.get("translate_to_english", False)
        )
        return True

    def _on_tray_language_changed(self, lang_code: str):
        self.config["language"] = lang_code
        save_config(self.config)
        self.orchestrator.update_config(self.config)
        self.tray.set_language_info(lang_code, self.config.get("translate_to_english", False))
        lang_name = lang_code.upper() if lang_code != "auto" else "Auto-Detect"
        self.tray.show_notification("FlowPilot Language Updated", f"Speech recognition set to: {lang_name}")

    def _on_tray_translate_toggled(self, enabled: bool):
        self.config["translate_to_english"] = enabled
        save_config(self.config)
        self.orchestrator.update_config(self.config)
        status_str = "ENABLED (Foreign speech -> English)" if enabled else "DISABLED (Standard native dictation)"
        self.tray.show_notification("FlowPilot Translation", f"Real-time speech translation: {status_str}")

    def _on_reinject_last(self):
        res = self.orchestrator.re_inject_last()
        from engine.text_injector import InjectionStatus
        prior_status = self.orchestrator.last_dictation.get("prior_injection_status")
        was_unverified = (prior_status == InjectionStatus.SENT_UNVERIFIED.value)

        if res.status == InjectionStatus.CONFIRMED_INSERTED:
            self.tray.show_notification("FlowPilot: Confirmed Inserted", "Last dictation physically verified in target window.")
        elif res.status == InjectionStatus.SENT_UNVERIFIED:
            msg = "Keystrokes sent to target window (unverified target buffer)."
            if was_unverified:
                msg += " Prior attempt was also unverified; please check for duplicate text."
            self.tray.show_notification("FlowPilot: Sent (Unverified)", msg, is_warning=True)
        elif res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE:
            self.tray.show_notification("FlowPilot: Recovery Saved", "Target window focus lost. Text preserved in recovery buffer (Shift+Alt+X to copy).", is_warning=True)
        else:
            self.tray.show_notification("FlowPilot Error", res.error_message or "Could not paste last dictation.", is_error=True)

    def _on_recopy_last(self):
        success = self.orchestrator.re_copy_last()
        if success:
            self.tray.show_notification("FlowPilot", "Last dictation copied to clipboard!")
        else:
            self.tray.show_notification("FlowPilot", "No previous dictation found to copy.")

    def show_companion_studio(self):
        # Open Studio window safely with keyboard focus enabled for custom creation
        if not self.studio_dlg:
            self.studio_dlg = CompanionStudioDialog()
            self.studio_dlg.applied.connect(self._on_companion_applied)
        self.studio_dlg.show()
        self.studio_dlg.raise_()
        self.studio_dlg.activateWindow()

    def _on_companion_applied(self, payload: dict):
        if payload.get("action") == "show_live":
            self.visibility.show_now()
            return
        if payload.get("action") == "rule_changed":
            self.visibility.refresh(force=True)
            return

        # Synchronize live companion with applied companion store state
        if "selected_asset_id" in payload:
            self.hud.set_visual_style(payload["selected_asset_id"])
        if "cat_palette" in payload:
            self.hud._cat_palette = payload["cat_palette"]
            self.hud._cat_pixmap_cache.clear()
        if "cat_sound" in payload:
            self.hud._cat_sound = bool(payload["cat_sound"])
        if "appearance_locked" in payload:
            self.hud._appearance_locked = bool(payload["appearance_locked"])
        if "motion_preset" in payload:
            self.hud._motion_preset = payload["motion_preset"]
        if "reduced_motion" in payload:
            self.hud._reduced_motion = bool(payload["reduced_motion"])
            self.hud._sync_animation_timer()
        if "snap_corner" in payload:
            self.hud.snap_to_corner(payload["snap_corner"])

        self.hud.update()
        self.visibility.refresh(force=True)

    def quit(self):
        print("[FlowPilot] Shutting down cleanly...")
        self.visibility.stop()
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
        if hasattr(self, 'dashboard') and self.dashboard:
            self.dashboard.close()
        self.hud.close()
        self.app.quit()

    def run(self):
        return self.app.exec()

def run_self_test() -> int:
    """Headless self-test validating that the bundled model and STT pipeline can transcribe acoustic audio offline."""
    import time
    import os
    print("=" * 65)
    print("FLOWPILOT STANDALONE OFFLINE DICTATION SELF-TEST")
    print("=" * 65)
    try:
        from engine.stt_engine import STTEngine
        from engine.config import load_config

        cfg = load_config()
        cfg["engine_mode"] = "local"
        cfg["local_model_size"] = "base"

        resolved_path = STTEngine.resolve_model_path("base")
        print(f"[Self-Test] Resolved offline model path: {resolved_path}")
        assert os.path.exists(resolved_path), f"Resolved model path does not exist: {resolved_path}"

        stt = STTEngine(cfg)
        print("[Self-Test] Loading model...")
        stt.preload_model()

        print("[Self-Test] Synthesizing speech fixture via SAPI...")
        import win32com.client
        import tempfile
        sp = win32com.client.Dispatch("SAPI.SpVoice")
        fs = win32com.client.Dispatch("SAPI.SpFileStream")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            tmp_wav = tf.name
        try:
            fs.Open(tmp_wav, 3)
            sp.AudioOutputStream = fs
            sp.Speak("FlowPilot offline dictation verified")
            fs.Close()
            with open(tmp_wav, "rb") as f:
                wav_bytes = f.read()
        finally:
            if os.path.isfile(tmp_wav):
                try:
                    os.unlink(tmp_wav)
                except Exception:
                    pass

        print(f"[Self-Test] Transcribing {len(wav_bytes)} bytes audio buffer...")
        t0 = time.time()
        res = stt.transcribe(wav_bytes)
        t_trans = time.time() - t0
        text = res.get("text", "") if isinstance(res, dict) else str(res)
        print(f"[Self-Test] Transcription output: '{text}' (in {t_trans:.2f}s)")
        assert any(k in text.lower() for k in ("offline", "flowpilot", "dictation", "verified")), f"Unexpected transcription: {text}"
        from engine.writing_intelligence import WritingIntelligence
        corrected = WritingIntelligence().polish(
            "schedule it for Tuesday actually Wednesday", mode="polished", style="professional"
        )["text"]
        assert "Wednesday" in corrected and "Tuesday" not in corrected, corrected
        print("[Self-Test] PASSED: Bundled model transcribed speech and local correction logic passed.")
        return 0
    except Exception as e:
        print(f"[Self-Test] FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

def main():
    # Handle Ctrl+C in terminal cleanly
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    if "--self-test" in sys.argv or "--smoke-test" in sys.argv:
        sys.exit(run_self_test())
    app = FlowPilotApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()
