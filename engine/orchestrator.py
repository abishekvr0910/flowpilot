import time
import threading
import json
from pathlib import Path
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

class AppState:
    IDLE = "IDLE"
    STARTING_RECORDING = "STARTING_RECORDING"
    RECORDING = "RECORDING"
    STOPPING_RECORDING = "STOPPING_RECORDING"
    TRANSCRIBING = "TRANSCRIBING"
    INSERTING_TEXT = "INSERTING_TEXT"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"

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
        self.state = AppState.IDLE
        self._state_lock = threading.RLock()
        self._stop_pending = False
        self.is_processing = False
        
        self.hotkey_service = Win32HotkeyService()
        self.hotkey_listener = None
        self.last_dictation: Dict[str, Any] = {}
        self._auto_stop_timer: Optional[threading.Timer] = None

        # Silence auto-stop tracking (Wispr Flow behavior)
        self._last_speech_time: float = 0.0
        self._last_speech_perf: float = 0.0
        self._speech_detected: bool = False
        self._speech_start_time: float = 0.0
        self.last_pipeline_timing: Dict[str, Any] = {}
        
        # Link audio level callback
        self.recorder.level_callback = self._on_audio_level

        # Asynchronously preload model in background to eliminate cold start
        threading.Thread(target=self.stt.preload_model, daemon=True, name="FlowPilot-ModelPreload").start()

    def _notify(self, state: str, extra: Optional[Dict[str, Any]] = None):
        legacy_map = {
            AppState.IDLE: "idle",
            AppState.STARTING_RECORDING: "starting",
            AppState.RECORDING: "listening",
            AppState.STOPPING_RECORDING: "stopping",
            AppState.TRANSCRIBING: "processing",
            AppState.INSERTING_TEXT: "formatting",
            AppState.SUCCESS: "pasted",
            AppState.ERROR: "error",
            AppState.CANCELLED: "cancelled"
        }
        legacy_state = legacy_map.get(state, state.lower() if isinstance(state, str) else "idle")
        payload = {
            "state": legacy_state,
            "app_state": state,
            "timestamp": time.time()
        }
        if extra:
            payload.update(extra)
        if self.on_state_change:
            self.on_state_change(payload)

    def _on_audio_level(self, level: float):
        if self.state == AppState.RECORDING or self.recorder.is_recording:
            self._notify("audio_level", {"level": round(level, 3)})

            # Wispr Flow behavior: intelligent silence auto-finalization
            if self.config.get("auto_stop_on_silence", True) and self.state == AppState.RECORDING:
                now = time.time()
                perf_now = time.perf_counter()
                # Threshold for speech presence (RMS level > 0.025)
                if level > 0.025:
                    if not self._speech_detected:
                        self._speech_detected = True
                        self._speech_start_time = now
                    self._last_speech_time = now
                    self._last_speech_perf = perf_now
                elif self._speech_detected:
                    speech_duration = self._last_speech_time - self._speech_start_time
                    silence_duration = now - self._last_speech_time
                    timeout = self.config.get("silence_timeout_sec", 0.85)
                    if speech_duration >= 0.3 and silence_duration >= timeout:
                        print(f"[Orchestrator] Post-speech silence ({silence_duration:.2f}s) detected. Auto-finalizing dictation (Wispr Flow mode)...")
                        self._speech_detected = False
                        self.stop_dictation_and_process()

    def _on_auto_stop(self):
        print("[Orchestrator] Maximum recording duration (120s) reached. Auto-stopping...")
        self.stop_dictation_and_process()

    def start_dictation(self):
        with self._state_lock:
            if self.state in (AppState.RECORDING, AppState.STARTING_RECORDING, AppState.STOPPING_RECORDING, AppState.TRANSCRIBING, AppState.INSERTING_TEXT):
                print(f"[Orchestrator] start_dictation ignored: currently in state {self.state}")
                return
            self.state = AppState.STARTING_RECORDING
            self._stop_pending = False
            self.is_processing = False
            self._last_speech_time = 0.0
            self._last_speech_perf = 0.0
            self._speech_detected = False
            self._speech_start_time = 0.0

        # 1. Capture target window immediately at T0
        self.target_window_info = WindowInspector.get_active_window_info()
        print(f"[Orchestrator] Active window target: {self.target_window_info.get('process_name')} ('{self.target_window_info.get('title')}')")

        # 2. Immediately notify UI of STARTING_RECORDING (zero latency visual feedback)
        self._notify(AppState.STARTING_RECORDING, {
            "target_app": self.target_window_info.get("process_name"),
            "mode": self.config.get("active_tone_mode")
        })

        # 3. Silence background audio asynchronously
        threading.Thread(target=self.ducker.start_ducking, daemon=True, name="FlowPilot-DuckerStart").start()

        def start_worker():
            try:
                self.recorder.start_recording()
                
                with self._state_lock:
                    if self.state != AppState.STARTING_RECORDING:
                        print(f"[Orchestrator] Recording startup aborted because state changed to {self.state}")
                        self.recorder.stop_recording()
                        return
                    if self._stop_pending:
                        print("[Orchestrator] Stop was requested during microphone initialization.")
                        self._stop_pending = False
                        self.state = AppState.RECORDING
                        self.stop_dictation_and_process()
                        return
                    self.state = AppState.RECORDING

                self.feedback.play_start()
                
                # Start safety auto-stop timer (120 seconds max recording)
                if self._auto_stop_timer:
                    self._auto_stop_timer.cancel()
                self._auto_stop_timer = threading.Timer(120.0, self._on_auto_stop)
                self._auto_stop_timer.daemon = True
                self._auto_stop_timer.start()

                self._notify(AppState.RECORDING, {
                    "target_app": self.target_window_info.get("process_name"),
                    "mode": self.config.get("active_tone_mode")
                })
            except Exception as e:
                with self._state_lock:
                    self.state = AppState.ERROR
                threading.Thread(target=self.ducker.stop_ducking, daemon=True).start()
                self.feedback.play_error()
                print(f"[Orchestrator Error] Failed to start recorder: {e}")
                self._notify(AppState.ERROR, {"message": str(e)})
                time.sleep(2.0)
                with self._state_lock:
                    if self.state == AppState.ERROR:
                        self.state = AppState.IDLE
                        self._notify(AppState.IDLE)

        threading.Thread(target=start_worker, daemon=True, name="FlowPilot-MicStarter").start()

    def cancel_dictation(self):
        """Emergency cancel: Discards recording immediately without transcribing or inserting."""
        with self._state_lock:
            if self.state == AppState.IDLE:
                return
            self.state = AppState.CANCELLED
            self._stop_pending = False
            self.is_processing = False

        print("[Orchestrator] Dictation cancelled by user.")
        if self._auto_stop_timer:
            self._auto_stop_timer.cancel()
            self._auto_stop_timer = None

        if self.recorder.is_recording:
            self.recorder.stop_recording()

        threading.Thread(target=self.ducker.stop_ducking, daemon=True).start()
        self.feedback.play_cancel()

        self._notify(AppState.CANCELLED, {"message": "Dictation discarded."})
        time.sleep(0.5)
        with self._state_lock:
            if self.state == AppState.CANCELLED:
                self.state = AppState.IDLE
                self._notify(AppState.IDLE)

    def stop_dictation_and_process(self):
        t_stop_action = time.perf_counter()
        with self._state_lock:
            if self.state == AppState.STARTING_RECORDING:
                print("[Orchestrator] Stop queued while starting recording.")
                self._stop_pending = True
                return
            if self.state != AppState.RECORDING:
                return

            self.state = AppState.STOPPING_RECORDING
            self.is_processing = True

        if self._auto_stop_timer:
            self._auto_stop_timer.cancel()
            self._auto_stop_timer = None

        self.feedback.play_stop()
        self._notify(AppState.STOPPING_RECORDING)

        # Immediately restore background audio asynchronously
        threading.Thread(target=self.ducker.stop_ducking, daemon=True, name="FlowPilot-DuckerStop").start()

        def process_worker(stop_action_time: float):
            try:
                # 1. Stop recorder and get audio data
                t_cap_start = time.perf_counter()
                wav_bytes = self.recorder.stop_recording()
                audio_array = self.recorder.get_last_audio_array()
                t_cap_end = time.perf_counter()

                if not wav_bytes:
                    print("[Orchestrator] Dictation was too brief or empty.")
                    with self._state_lock:
                        self.state = AppState.IDLE
                        self.is_processing = False
                    self._notify(AppState.IDLE, {"notice": "Audio too short."})
                    return

                t_audio_finalized = time.perf_counter()

                # 2. Transition to TRANSCRIBING
                with self._state_lock:
                    self.state = AppState.TRANSCRIBING
                self._notify(AppState.TRANSCRIBING)

                # 3. Transcribe audio (STT) - pass zero-copy float32 array if available
                t_stt_start = time.perf_counter()
                stt_input = audio_array if audio_array is not None else wav_bytes
                stt_result = self.stt.transcribe(stt_input)
                t_stt_end = time.perf_counter()

                raw_text = stt_result.get("text", "")
                detected_lang = stt_result.get("detected_language", "unknown")
                stt_duration = round(t_stt_end - t_stt_start, 3)
                print(f"[Orchestrator] STT completed ({stt_duration}s, lang={detected_lang}, chars={len(raw_text)}).")

                if not raw_text or not raw_text.strip():
                    with self._state_lock:
                        self.state = AppState.IDLE
                        self.is_processing = False
                    self._notify(AppState.IDLE, {"notice": "No speech detected."})
                    return

                # 4. Transition to INSERTING_TEXT
                with self._state_lock:
                    self.state = AppState.INSERTING_TEXT
                self._notify(AppState.INSERTING_TEXT, {"char_count": len(raw_text)})

                # Post-process via ContextProcessor
                t_clean_start = time.perf_counter()
                formatted_text = self.processor.process(raw_text, self.target_window_info)
                if self.personalization:
                    expanded_text, trigger = self.personalization.expand_snippets(formatted_text)
                    if trigger:
                        print("[Orchestrator] Expanded voice snippet trigger matched.")
                        formatted_text = expanded_text
                t_clean_end = time.perf_counter()
                format_duration = round(t_clean_end - t_clean_start, 3)
                print(f"[Orchestrator] Formatting completed ({format_duration}s, chars={len(formatted_text)}).")

                # 5. Inject formatted text into target window with confirmed fallback
                t_inj_start = time.perf_counter()
                target_hwnd = self.target_window_info.get("hwnd")
                injection_method = "clipboard_paste"
                success = TextInjector.inject(formatted_text, target_hwnd)
                if not success:
                    print("[Orchestrator] Standard clipboard paste failed. Falling back to direct SendInput Unicode typing...")
                    injection_method = "sendinput_unicode"
                    success = TextInjector.inject_unicode_sendinput(formatted_text, target_hwnd)
                t_inj_end = time.perf_counter()

                # Stage-level high-precision timing calculations
                user_stop_to_cap_ms = round((t_cap_end - stop_action_time) * 1000, 2)
                cap_to_finalize_ms = round((t_audio_finalized - t_cap_end) * 1000, 2)
                finalize_to_stt_ms = round((t_stt_start - t_audio_finalized) * 1000, 2)
                stt_ms = round((t_stt_end - t_stt_start) * 1000, 2)
                cleanup_ms = round((t_clean_end - t_clean_start) * 1000, 2)
                inj_ms = round((t_inj_end - t_inj_start) * 1000, 2)
                stop_to_visible_text_ms = round((t_inj_end - stop_action_time) * 1000, 2)
                acoustic_to_visible_text_ms = round((t_inj_end - self._last_speech_perf) * 1000, 2) if self._last_speech_perf > 0 else None

                self.last_pipeline_timing = {
                    "stop_to_capture_shutdown_ms": user_stop_to_cap_ms,
                    "capture_to_audio_finalization_ms": cap_to_finalize_ms,
                    "audio_finalization_to_stt_start_ms": finalize_to_stt_ms,
                    "transcription_ms": stt_ms,
                    "cleanup_ms": cleanup_ms,
                    "text_insertion_ms": inj_ms,
                    "stop_action_to_visible_text_ms": stop_to_visible_text_ms,
                    "acoustic_end_to_visible_text_ms": acoustic_to_visible_text_ms
                }

                print(
                    f"[Latency Breakdown] Stop->Cap: {user_stop_to_cap_ms}ms | Finalize: {cap_to_finalize_ms}ms | "
                    f"STT: {stt_ms}ms | Clean: {cleanup_ms}ms | Inject: {inj_ms}ms | "
                    f"StopAction->VisibleText: {stop_to_visible_text_ms}ms"
                    + (f" | AcousticEnd->VisibleText: {acoustic_to_visible_text_ms}ms" if acoustic_to_visible_text_ms else "")
                )

                # 6. Save into history and recovery buffer
                total_duration = round(time.time() - start_time, 2)
                save_text = self.config.get("save_history_text", False)
                history_entry = {
                    "id": int(time.time() * 1000),
                    "raw_text": raw_text if save_text else "",
                    "formatted_text": formatted_text if save_text else "",
                    "target_app": self.target_window_info.get("process_name"),
                    "language": detected_lang,
                    "duration_sec": total_duration,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "injection_status": "SUCCESS" if success else "FAILED",
                    "injection_method": injection_method
                }
                # Keep active formatted_text in volatile memory for Tray 'Copy Last Dictation'
                self.last_dictation = {**history_entry, "formatted_text": formatted_text}
                
                # Write local telemetry for pilot program metrics (strictly anonymous, no text)
                self._record_telemetry({
                    "timestamp": time.time(),
                    "datetime": history_entry["timestamp"],
                    "target_app": history_entry["target_app"],
                    "audio_duration_sec": round(len(wav_bytes) / 32000.0, 2),
                    "stt_duration_sec": stt_duration,
                    "format_duration_sec": format_duration,
                    "total_duration_sec": total_duration,
                    "stop_to_visible_text_ms": stop_to_visible_text_ms,
                    "acoustic_end_to_visible_text_ms": acoustic_to_visible_text_ms,
                    "char_count": len(formatted_text),
                    "injection_method": injection_method,
                    "injection_success": success
                })

                history = self.config.get("history", [])
                history.insert(0, history_entry)
                self.config["history"] = history[:50]
                save_config(self.config)

                if not success:
                    print("[Orchestrator Error] Text injection failed. Preserving text in clipboard for manual paste.")
                    TextInjector._safe_clipboard_copy(formatted_text)
                    with self._state_lock:
                        self.state = AppState.ERROR
                        self.is_processing = False
                    self.feedback.play_error()
                    self._notify(AppState.ERROR, {
                        "message": "Paste failed (saved to clipboard)",
                        "notice": "Paste failed - saved to clipboard"
                    })
                    time.sleep(2.0)
                    with self._state_lock:
                        if self.state == AppState.ERROR:
                            self.state = AppState.IDLE
                            self._notify(AppState.IDLE)
                    return

                # 7. Transition to SUCCESS only when injection was confirmed
                with self._state_lock:
                    self.state = AppState.SUCCESS
                    self.is_processing = False
                self._notify(AppState.SUCCESS, {
                    "text": formatted_text,
                    "total_duration": total_duration,
                    "history_entry": history_entry
                })

                # Show "Pasted!" briefly (0.8s), then transition to IDLE
                time.sleep(0.8)
                with self._state_lock:
                    if self.state == AppState.SUCCESS:
                        self.state = AppState.IDLE
                        self._notify(AppState.IDLE)

            except Exception as e:
                print(f"[Orchestrator Error] Processing failed: {e}")
                with self._state_lock:
                    self.state = AppState.ERROR
                    self.is_processing = False
                self._notify(AppState.ERROR, {"message": str(e)})
                time.sleep(2.0)
                with self._state_lock:
                    if self.state == AppState.ERROR:
                        self.state = AppState.IDLE
                        self._notify(AppState.IDLE)

        threading.Thread(target=process_worker, args=(t_stop_action,), daemon=True, name="FlowPilot-Processor").start()

    def toggle_dictation(self):
        with self._state_lock:
            cur = self.state

        if cur == AppState.IDLE:
            self.start_dictation()
        elif cur == AppState.STARTING_RECORDING:
            with self._state_lock:
                self._stop_pending = True
            print("[Orchestrator] Stop queued while starting recording.")
        elif cur == AppState.RECORDING:
            self.stop_dictation_and_process()
        elif cur in (AppState.STOPPING_RECORDING, AppState.TRANSCRIBING, AppState.INSERTING_TEXT):
            print(f"[Orchestrator] Shortcut pressed while {cur}. Displaying progress notification.")
            self._notify(cur, {"notice": "Processing dictation. Please wait..."})
        elif cur == AppState.SUCCESS:
            self.start_dictation()
        elif cur in (AppState.ERROR, AppState.CANCELLED):
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
                if clean_hk.lower() != "f9":
                    self.hotkey_service.register("F9", self.start_dictation, on_release=self.stop_dictation_and_process)
                if clean_hk.lower() != "ctrl+alt+space":
                    self.hotkey_service.register("Ctrl+Alt+Space", self.toggle_dictation)
            else:
                # Toggle: press once to start, press again to stop
                self.hotkey_service.register(clean_hk, self.toggle_dictation)
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

    def _record_telemetry(self, data: Dict[str, Any]):
        """Records local-only anonymous telemetry for pilot metrics. Zero network egress."""
        if not self.config.get("telemetry_enabled", False):
            return
        try:
            log_dir = Path.home() / ".flowpilot"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "dictation_telemetry.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception:
            pass
