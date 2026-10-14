import time
import threading
from typing import Dict, Any, Callable, Optional, List
from engine.config import load_config, save_config
from engine.audio_recorder import AudioRecorder
from engine.window_inspector import WindowInspector
from engine.stt_engine import STTEngine
from engine.context_processor import ContextProcessor
from engine.text_injector import TextInjector
from engine.audio_ducker import AudioDucker
from engine.hotkey_service import Win32HotkeyService
from engine.audio_feedback import AudioFeedback
from engine.personalization import PersonalizationEngine

class FlowOrchestrator:
    def __init__(self, on_state_change: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.config = load_config()
        self.on_state_change = on_state_change
        
        self.personalization = PersonalizationEngine()
        self.recorder = AudioRecorder()
        self.stt = STTEngine(self.config, personalization=self.personalization)
        self.processor = ContextProcessor(self.config, personalization=self.personalization)
        self.ducker = AudioDucker(duck_mode="mute")
        self.feedback = AudioFeedback(enabled=self.config.get("sound_effects_enabled", True))
        
        self.target_window_info: Dict[str, Any] = {}
        self.is_processing = False
        self.hotkey_service = Win32HotkeyService()
        self.hotkey_listener = None
        self.last_dictation: Dict[str, Any] = {}
        self._auto_stop_timer: Optional[threading.Timer] = None
        
        # Link audio level callback
        self.recorder.level_callback = self._on_audio_level

    def _notify(self, state: str, extra: Optional[Dict[str, Any]] = None):
        payload = {"state": state, "timestamp": time.time()}
        if extra:
            payload.update(extra)
        if self.on_state_change:
            self.on_state_change(payload)

    def _on_audio_level(self, level: float):
        if self.recorder.is_recording:
            self._notify("audio_level", {"level": round(level, 3)})

    def _on_auto_stop(self):
        print("[Orchestrator] Maximum recording duration (120s) reached. Auto-stopping...")
        self.stop_dictation_and_process()

    def start_dictation(self):
        if self.recorder.is_recording or self.is_processing:
            return

        # 1. Capture the exact window handle that has focus RIGHT NOW
        self.target_window_info = WindowInspector.get_active_window_info()
        print(f"[Orchestrator] Active window target: {self.target_window_info.get('process_name')} ('{self.target_window_info.get('title')}')")

        # 2. Silence background audio (YouTube, Spotify, etc.) so mic captures clean voice
        self.ducker.start_ducking()

        # 3. Start audio recording
        try:
            self.recorder.start_recording()
            self.feedback.play_start()
            
            # Start safety auto-stop timer (120 seconds max recording)
            if self._auto_stop_timer:
                self._auto_stop_timer.cancel()
            self._auto_stop_timer = threading.Timer(120.0, self._on_auto_stop)
            self._auto_stop_timer.daemon = True
            self._auto_stop_timer.start()

            self._notify("listening", {
                "target_app": self.target_window_info.get("process_name"),
                "mode": self.config.get("active_tone_mode")
            })
        except Exception as e:
            self.ducker.stop_ducking()
            self.feedback.play_error()
            print(f"[Orchestrator Error] Failed to start recorder: {e}")
            self._notify("error", {"message": str(e)})

    def cancel_dictation(self):
        """Emergency cancel: Discards recording immediately without transcribing or inserting."""
        if not self.recorder.is_recording and not self.is_processing:
            return

        print("[Orchestrator] Dictation cancelled by user.")
        if self._auto_stop_timer:
            self._auto_stop_timer.cancel()
            self._auto_stop_timer = None

        if self.recorder.is_recording:
            self.recorder.stop_recording()

        self.ducker.stop_ducking()
        self.feedback.play_cancel()
        self.is_processing = False

        self._notify("cancelled", {"message": "Dictation discarded."})
        time.sleep(0.5)
        self._notify("idle")

    def stop_dictation_and_process(self):
        if not self.recorder.is_recording or self.is_processing:
            return

        if self._auto_stop_timer:
            self._auto_stop_timer.cancel()
            self._auto_stop_timer = None

        self.is_processing = True
        self.feedback.play_stop()
        self._notify("processing")

        # Immediately restore background audio
        self.ducker.stop_ducking()

        def worker():
            try:
                # 1. Stop recorder and get WAV bytes
                wav_bytes = self.recorder.stop_recording()
                if not wav_bytes:
                    print("[Orchestrator] Dictation was too brief or empty.")
                    self._notify("idle")
                    self.is_processing = False
                    return

                # 2. Transcribe audio (STT)
                start_time = time.time()
                stt_result = self.stt.transcribe(wav_bytes)
                raw_text = stt_result.get("text", "")
                detected_lang = stt_result.get("detected_language", "unknown")
                stt_duration = round(time.time() - start_time, 2)
                print(f"[Orchestrator] STT done ({stt_duration}s, lang={detected_lang}): {raw_text}")

                if not raw_text:
                    self._notify("idle", {"message": "No speech detected."})
                    self.is_processing = False
                    return

                # 3. Post-process / Format via LLM with context
                self._notify("formatting", {"raw_text": raw_text})
                format_start = time.time()
                formatted_text = self.processor.process(raw_text, self.target_window_info)
                format_duration = round(time.time() - format_start, 2)
                print(f"[Orchestrator] Formatted ({format_duration}s): {formatted_text}")

                # 4. Check Voice Snippets expansion (e.g. "insert my calendly")
                if self.personalization:
                    expanded_text, trigger = self.personalization.expand_snippets(formatted_text)
                    if trigger:
                        print(f"[Orchestrator] Expanded voice snippet trigger: '{trigger}'")
                        formatted_text = expanded_text

                # 5. Inject formatted text into target window
                target_hwnd = self.target_window_info.get("hwnd")
                success = TextInjector.inject(formatted_text, target_hwnd)

                # 5. Save into history and recovery buffer
                total_duration = round(time.time() - start_time, 2)
                history_entry = {
                    "id": int(time.time() * 1000),
                    "raw_text": raw_text,
                    "formatted_text": formatted_text,
                    "target_app": self.target_window_info.get("process_name"),
                    "language": detected_lang,
                    "duration_sec": total_duration,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                self.last_dictation = history_entry
                
                # Keep last 50 history entries
                history = self.config.get("history", [])
                history.insert(0, history_entry)
                self.config["history"] = history[:50]
                save_config(self.config)

                self._notify("pasted", {
                    "text": formatted_text,
                    "total_duration": total_duration,
                    "history_entry": history_entry
                })

            except Exception as e:
                print(f"[Orchestrator Error] Processing failed: {e}")
                self._notify("error", {"message": str(e)})
            finally:
                self.is_processing = False
                time.sleep(1.2)  # Keep pill showing "Pasted!" briefly before returning to idle
                # Only notify idle if a new recording hasn't already been started
                if not self.recorder.is_recording and not self.is_processing:
                    self._notify("idle")

        threading.Thread(target=worker, daemon=True).start()

    def toggle_dictation(self):
        if self.recorder.is_recording:
            self.stop_dictation_and_process()
        else:
            self.start_dictation()

    def update_config(self, new_config: Dict[str, Any]):
        old_hk = self.config.get("hotkey")
        old_mode = self.config.get("hotkey_mode")
        self.config.update(new_config)
        save_config(self.config)
        # Update submodules
        self.stt.config = self.config
        self.processor.config = self.config
        print("[Orchestrator] Configuration updated.")

        # Re-bind hotkeys dynamically if shortcut or mode changed
        new_hk = self.config.get("hotkey")
        new_mode = self.config.get("hotkey_mode")
        if (new_hk and new_hk != old_hk) or (new_mode and new_mode != old_mode):
            print(f"[Orchestrator] Re-registering hotkey service with updated shortcut '{new_hk}' (mode={new_mode})...")
            self.stop_hotkey_listener()
            from engine.hotkey_service import Win32HotkeyService
            self.hotkey_service = Win32HotkeyService()
            self.start_hotkey_listener()

    def re_copy_last(self) -> bool:
        """Copies the last dictation text directly to clipboard."""
        return TextInjector.re_copy_last()

    def re_inject_last(self) -> bool:
        """Re-injects the last dictation text into the currently active or last target window."""
        text = self.last_dictation.get("formatted_text") or TextInjector.last_injected_text
        if not text:
            return False
        cur_target = WindowInspector.get_active_window_info().get("hwnd") or self.target_window_info.get("hwnd")
        return TextInjector.inject(text, cur_target)

    def start_hotkey_listener(self):
        """
        Registers native Win32 global hotkeys using RegisterHotKey.
        Supports both Toggle Mode and Push-to-Talk Mode.
        - Primary shortcut from config (default: Ctrl + Shift + Space)
        - Alternative toggle: Ctrl + Alt + Space
        - Single-key toggle: F9
        """
        try:
            primary_hk = self.config.get("hotkey", "Ctrl+Shift+Space")
            clean_hk = primary_hk.replace("<", "").replace(">", "").strip()
            mode = self.config.get("hotkey_mode", "toggle")

            if mode == "push_to_talk":
                # Push-to-talk: keydown starts, keyup stops
                self.hotkey_service.register(clean_hk, self.start_dictation, on_release=self.stop_dictation_and_process)
            else:
                # Toggle: press once to start, press again to stop
                self.hotkey_service.register(clean_hk, self.toggle_dictation)

            # Register backup toggles if distinct
            if clean_hk.lower() != "ctrl+alt+space":
                self.hotkey_service.register("Ctrl+Alt+Space", self.toggle_dictation)
            if clean_hk.lower() != "f9":
                self.hotkey_service.register("F9", self.toggle_dictation)
            
            success = self.hotkey_service.start(timeout=3.0)
            if success:
                print(f"[Orchestrator] Native Win32 Hotkey Service active: '{clean_hk}' (mode={mode}), 'Ctrl + Alt + Space', 'F9'")
            else:
                print(f"[Orchestrator Warning] Win32 Hotkey Service encountered errors: {self.hotkey_service.stats['errors']}")
        except Exception as e:
            print(f"[Orchestrator Error] Failed to start hotkey service: {e}")

    def stop_hotkey_listener(self):
        """
        Unregisters all native Win32 hotkeys and terminates the message loop cleanly.
        """
        if self.hotkey_service:
            self.hotkey_service.stop()
            print("[Orchestrator] Hotkey service stopped.")

    def stop(self):
        """Clean shutdown of all orchestrator services."""
        self.stop_hotkey_listener()
