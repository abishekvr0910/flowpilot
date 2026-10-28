"""Feature 28: Dictation sessions and persistent microphone ownership."""
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Callable, Optional, List
from engine.config import OBSOLETE_CLOUD_KEYS, load_config, local_only_config, save_config
from engine.audio_recorder import AudioRecorder
from engine.window_inspector import WindowInspector
from engine.stt_engine import STTEngine
from engine.context_processor import ContextProcessor
from engine.text_injector import TextInjector
from engine.audio_ducker import AudioDucker
from engine.audio_feedback import AudioFeedback
from engine.hotkey_service import get_hotkey_service, Win32HotkeyService, dictation_hotkey_conflict, parse_hotkey_string
from engine.personalization import PersonalizationEngine, get_shared_personalization
from engine.session import DictationSession, SessionState
from engine.audio_devices import resolve_audio_input, build_device_selection, migrate_legacy_audio_config, refresh_audio_devices
from engine.pilot_telemetry import append_local_event

logger = logging.getLogger("FlowPilot.Orchestrator")


def injection_completion_timing(
    stop_action_at: float,
    completion_at: float,
    acoustic_end_at: float = 0.0,
) -> Dict[str, Any]:
    """Time the injection result without claiming text was observed on screen."""
    return {
        "stop_action_to_injection_result_ms": round((completion_at - stop_action_at) * 1000, 2),
        "acoustic_end_to_injection_result_ms": (
            round((completion_at - acoustic_end_at) * 1000, 2)
            if acoustic_end_at > 0 else None
        ),
        "stop_action_to_visible_text_ms": None,
        "visible_delivery_status": "not_measured",
    }


class AppState:
    IDLE = "IDLE"
    STARTING_RECORDING = "STARTING_RECORDING"
    RECORDING = "RECORDING"
    STOPPING_RECORDING = "STOPPING_RECORDING"
    TRANSCRIBING = "TRANSCRIBING"
    VALIDATING = "VALIDATING"
    INSERTING_TEXT = "INSERTING_TEXT"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"

class FlowOrchestrator:
    def __init__(self, on_state_change: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.config = load_config()
        self.on_state_change = on_state_change

        self.personalization = get_shared_personalization()
        migrate_legacy_audio_config(self.config)
        self._device_selection = self.config["audio_input_selection"]
        self._last_device_resolution = resolve_audio_input(self._device_selection)
        self.recorder = AudioRecorder(device=self._last_device_resolution.device_index)
        self.stt = STTEngine(self.config, personalization=self.personalization)
        self.processor = ContextProcessor(self.config, personalization=self.personalization)
        self.ducker = AudioDucker(duck_mode="mute")
        self.feedback = AudioFeedback(enabled=self.config.get("sound_effects_enabled", True))

        self.target_window_info: Dict[str, Any] = {}
        self.state = AppState.IDLE
        self._current_session: Optional[DictationSession] = None
        self._state_lock = threading.RLock()
        self._success_generation = 0
        self._stop_pending = False
        self.is_processing = False

        self.hotkey_service = get_hotkey_service()
        self.hotkey_listener = None
        self._auxiliary_hotkeys: Dict[str, Callable[[], None]] = {}
        self.last_dictation: Dict[str, Any] = {}
        self._auto_stop_timer: Optional[threading.Timer] = None
        self._capture_watchdog_stop = threading.Event()
        self._mute_hotkey_registered = False

        # Silence auto-stop tracking (Wispr Flow behavior)
        self._last_speech_time: float = 0.0
        self._last_speech_perf: float = 0.0
        self._speech_detected: bool = False
        self._speech_start_time: float = 0.0
        self.last_pipeline_timing: Dict[str, Any] = {}
        self._tap_latch: Optional[Any] = None
        self._idle_unload_timer: Optional[threading.Timer] = None
        self._idle_unload_timeout_sec: float = float(self.config.get("idle_model_unload_sec", 600.0))

        # Universal Selection Rewriter & Undo Latch (WP-2)
        from engine.selection_rewriter import SelectionRewriter
        self.selection_rewriter = SelectionRewriter()

        # Link audio level callback
        self.recorder.level_callback = self._on_audio_level
        self._pending_model_switch: Optional[str] = None

        # Asynchronously preload model in background to eliminate cold start
        threading.Thread(target=self.stt.preload_model, daemon=True, name="FlowPilot-ModelPreload").start()

        # Tier 2 Local Text Repair (process-isolated SLM sandbox)
        self.text_repair: Optional[Any] = None
        if self.config.get("local_text_repair_enabled", False):
            try:
                from engine.local_text_repair import LocalTextRepair
                self.text_repair = LocalTextRepair(self.config)
                self.text_repair.warmup_async()
                logger.info("LocalTextRepair initialized; non-blocking background warmup started.")
            except Exception as e:
                logger.warning("LocalTextRepair initialization failed: %s", e)

        # Start idle unloader schedule
        self._schedule_idle_unloader()

    def _cancel_idle_unloader(self):
        with self._state_lock:
            if getattr(self, "_idle_unload_timer", None) is not None:
                self._idle_unload_timer.cancel()
                self._idle_unload_timer = None

    def _schedule_idle_unloader(self):
        with self._state_lock:
            if getattr(self, "_idle_unload_timer", None) is not None:
                self._idle_unload_timer.cancel()
                self._idle_unload_timer = None
            timeout = getattr(self, "_idle_unload_timeout_sec", 600.0)
            if timeout > 0:
                t = threading.Timer(timeout, self._on_idle_unload_timeout)
                t.daemon = True
                self._idle_unload_timer = t
                t.start()

    def _on_idle_unload_timeout(self):
        with self._state_lock:
            rec = getattr(self.recorder, "is_recording", False) if hasattr(self, "recorder") else False
            if self.state != AppState.IDLE or rec or getattr(self, "is_processing", False):
                return
        logger.info("[Orchestrator] Idle timeout reached. Unloading inactive models to free system RAM.")
        try:
            if hasattr(self, "stt") and self.stt is not None:
                self.stt.unload_model()
        except Exception as e:
            logger.debug("STT model unload exception: %s", e)
        try:
            if hasattr(self, "text_repair") and self.text_repair is not None:
                self.text_repair.unload_model()
        except Exception as e:
            logger.debug("Text repair model unload exception: %s", e)

    def _schedule_correction_check(self, target_hwnd: Optional[int], injected_text: str):
        if not target_hwnd:
            return
        def _check():
            try:
                buf = TextInjector.read_window_buffer(target_hwnd)
                if buf:
                    from engine.writing_intelligence import get_correction_detector
                    get_correction_detector().inspect_buffer_change(buf, hwnd=target_hwnd)
            except Exception as e:
                logger.debug("Correction inspection exception: %s", e)

        for delay in (5.0, 15.0):
            t = threading.Timer(delay, _check)
            t.daemon = True
            t.start()

    def _notify(self, state: str, extra: Optional[Dict[str, Any]] = None):
        legacy_map = {
            AppState.IDLE: "idle",
            AppState.STARTING_RECORDING: "starting",
            AppState.RECORDING: "listening",
            AppState.STOPPING_RECORDING: "stopping",
            AppState.TRANSCRIBING: "processing",
            AppState.VALIDATING: "validating",
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

            # A muted session remains open. Do not let the intentional zero
            # level trigger silence auto stop while the user is thinking.
            if getattr(self.recorder, "is_muted", False):
                return

            # Intelligent silence auto-finalization (when enabled)
            if self.config.get("auto_stop_on_silence", False) and self.state == AppState.RECORDING:
                now = time.time()
                perf_now = time.perf_counter()
                # Threshold for speech presence (RMS level > 0.015 for sensitivity)
                if level > 0.015:
                    if not self._speech_detected:
                        self._speech_detected = True
                        self._speech_start_time = now
                    self._last_speech_time = now
                    self._last_speech_perf = perf_now
                elif self._speech_detected:
                    speech_duration = self._last_speech_time - self._speech_start_time
                    silence_duration = now - self._last_speech_time
                    timeout = self.config.get("silence_timeout_sec", 2.5)
                    if speech_duration >= 0.5 and silence_duration >= timeout:
                        print(f"[Orchestrator] Post-speech silence ({silence_duration:.2f}s) detected. Auto-finalizing dictation...")
                        self._speech_detected = False
                        self.stop_dictation_and_process()

    def _on_auto_stop(self):
        print("[Orchestrator] Maximum recording duration (120s) reached. Auto-stopping...")
        self.stop_dictation_and_process()

    def _start_capture_watchdog(self, active_session: DictationSession) -> None:
        """Stop a session when its microphone callback reports loss or goes quiet."""
        self._capture_watchdog_stop.set()
        stop_event = threading.Event()
        self._capture_watchdog_stop = stop_event

        def watch():
            while not stop_event.wait(0.25):
                error = self.recorder.capture_health_error()
                if not error:
                    continue
                with self._state_lock:
                    if active_session != self._current_session or self.state != AppState.RECORDING:
                        return
                    active_session.transition_to(SessionState.ERROR)
                    self.state = AppState.ERROR
                    self.is_processing = False
                stop_event.set()
                if self._auto_stop_timer:
                    self._auto_stop_timer.cancel()
                    self._auto_stop_timer = None
                self.recorder.close()
                threading.Thread(target=self.ducker.stop_ducking, daemon=True).start()
                self.feedback.play_error()
                self._notify(AppState.ERROR, {
                    "message": error, "session_id": active_session.session_id,
                    "notice": "Microphone stopped. No text was inserted.",
                })
                time.sleep(2.0)
                with self._state_lock:
                    if active_session == self._current_session and self.state == AppState.ERROR:
                        active_session.transition_to(SessionState.IDLE)
                        self.state = AppState.IDLE
                        self._notify(AppState.IDLE)
                        self._schedule_idle_unloader()
                return

        threading.Thread(target=watch, daemon=True, name="FlowPilot-CaptureWatchdog").start()

    def start_selection_rewrite(self) -> bool:
        """Captures active selection from foreground window and begins voice rewrite session."""
        if self.state != AppState.IDLE:
            return False
        sel_text, hwnd, title, proc_name = self.selection_rewriter.capture_selection()
        if not sel_text or not sel_text.strip():
            return False
        self.start_dictation(is_selection_rewrite=True, pre_selected_text=sel_text)
        return True

    def start_dictation(self, translation_mode: Optional[bool] = None, is_selection_rewrite: bool = False, pre_selected_text: Optional[str] = None):
        self._cancel_idle_unloader()
        with self._state_lock:
            if self.state in (AppState.RECORDING, AppState.STARTING_RECORDING, AppState.STOPPING_RECORDING, AppState.TRANSCRIBING, AppState.VALIDATING, AppState.INSERTING_TEXT):
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
        # Window titles can contain document names or private text. Do not log them.
        print("[Orchestrator] Active window target captured locally.")

        # Create new dictation session with unique session token
        is_translate = translation_mode if translation_mode is not None else self.config.get("translate_to_english", False)
        session = DictationSession(
            target_window_info=self.target_window_info,
            tone_mode=self.config.get("active_tone_mode", "general")
        )
        session.task = "translate" if is_translate else "transcribe"
        session.language = self.config.get("language", "auto")
        session.model_size = self.config.get("local_model_size", "base")
        session.is_selection_rewrite = is_selection_rewrite
        session.selected_text = pre_selected_text
        with self._state_lock:
            self._current_session = session

        # 2. Immediately notify UI of STARTING_RECORDING (zero latency visual feedback)
        self._notify(AppState.STARTING_RECORDING, {
            "session_id": session.session_id,
            "target_app": self.target_window_info.get("process_name"),
            "mode": self.config.get("active_tone_mode"),
            "task": session.task,
            "language": session.language
        })

        # 3. Silence background audio asynchronously
        threading.Thread(target=self.ducker.start_ducking, daemon=True, name="FlowPilot-DuckerStart").start()

        def start_worker(active_session: DictationSession):
            try:
                # Enumeration can change since startup or the last settings save.
                if not self.recorder.has_healthy_hot_stream():
                    self.recorder.close()
                    refresh_audio_devices()
                resolution = resolve_audio_input(self._device_selection)
                previous = self._last_device_resolution
                if resolution.device_index != self.recorder.device:
                    self.recorder.set_device(resolution.device_index)
                elif (isinstance(self._device_selection, dict)
                      and self._device_selection.get("mode") == "default"
                      and resolution.device_info != previous.device_info):
                    self.recorder.close()
                self._last_device_resolution = resolution
                if resolution.device_index is not None and resolution.device_index < 0:
                    raise RuntimeError(resolution.error_message or "Select an available microphone in Settings.")
                self.recorder.start_recording()

                with self._state_lock:
                    if active_session.is_cancelled or active_session != self._current_session or self.state != AppState.STARTING_RECORDING:
                        print(f"[Orchestrator] Recording startup aborted because state changed or session was cancelled (state={self.state})")
                        self.recorder.stop_recording()
                        return
                    if self._stop_pending:
                        print("[Orchestrator] Stop was requested during microphone initialization.")
                        self._stop_pending = False
                        self.state = AppState.RECORDING
                        active_session.transition_to(SessionState.RECORDING)
                        self.stop_dictation_and_process()
                        return
                    self.state = AppState.RECORDING
                    active_session.transition_to(SessionState.RECORDING)

                self.feedback.play_start()

                # Start safety auto-stop timer (120 seconds max recording)
                if self._auto_stop_timer:
                    self._auto_stop_timer.cancel()
                self._auto_stop_timer = threading.Timer(120.0, self._on_auto_stop)
                self._auto_stop_timer.daemon = True
                self._auto_stop_timer.start()

                self._notify(AppState.RECORDING, {
                    "session_id": active_session.session_id,
                    "target_app": self.target_window_info.get("process_name"),
                    "mode": self.config.get("active_tone_mode")
                })
                self._start_capture_watchdog(active_session)
            except Exception as e:
                with self._state_lock:
                    if active_session.is_cancelled or self.state == AppState.CANCELLED:
                        print(f"[Orchestrator] Exception after cancellation (state={self.state}); preserving CANCELLED state.")
                        return
                    active_session.transition_to(SessionState.ERROR)
                    self.state = AppState.ERROR
                threading.Thread(target=self.ducker.stop_ducking, daemon=True).start()
                self.feedback.play_error()
                print(f"[Orchestrator Error] Failed to start recorder: {e}")
                self._notify(AppState.ERROR, {"message": str(e), "session_id": active_session.session_id})
                time.sleep(2.0)
                with self._state_lock:
                    if self.state == AppState.ERROR:
                        self.state = AppState.IDLE
                        self._notify(AppState.IDLE)

        threading.Thread(target=start_worker, args=(session,), daemon=True, name="FlowPilot-MicStarter").start()

    def cancel_dictation(self):
        """Emergency cancel: Discards recording immediately without transcribing or inserting."""
        self._capture_watchdog_stop.set()
        with self._state_lock:
            if self.state == AppState.IDLE and (not self._current_session or not self._current_session.is_active()):
                return
            if self._current_session:
                self._current_session.cancel("user_cancelled")
            self.state = AppState.CANCELLED
            self._stop_pending = False
            self.is_processing = False

        print("[Orchestrator] Dictation cancelled by user.")
        if self._auto_stop_timer:
            self._auto_stop_timer.cancel()
            self._auto_stop_timer = None

        if self.recorder.is_recording:
            try:
                self.recorder.stop_recording()
            except RuntimeError as exc:
                logger.warning("Recording was discarded after capture failure: %s", exc)

        if hasattr(self, "_tap_latch") and self._tap_latch:
            self._tap_latch.reset()

        # Always guarantee audio ducking restoration immediately on cancel
        threading.Thread(target=self.ducker.stop_ducking, daemon=True).start()
        self.feedback.play_cancel()

        self._notify(AppState.CANCELLED, {"message": "Dictation discarded."})
        time.sleep(0.5)
        with self._state_lock:
            if self.state == AppState.CANCELLED:
                self.state = AppState.IDLE
                self._notify(AppState.IDLE)
        self._apply_pending_model_switch_if_idle()

    def stop_dictation_and_process(self):
        t_stop_action = time.perf_counter()
        with self._state_lock:
            if self.state == AppState.STARTING_RECORDING:
                print("[Orchestrator] Stop queued while starting recording.")
                self._stop_pending = True
                return
            if self.state != AppState.RECORDING:
                return

            session = self._current_session
            if not session or session.is_cancelled:
                print("[Orchestrator] Stop ignored: session is null or cancelled.")
                return

            self.state = AppState.STOPPING_RECORDING
            session.transition_to(SessionState.FINALIZING)
            self.is_processing = True

        self._capture_watchdog_stop.set()

        if self._auto_stop_timer:
            self._auto_stop_timer.cancel()
            self._auto_stop_timer = None

        self.feedback.play_stop()
        self._notify(AppState.STOPPING_RECORDING, {"session_id": session.session_id})

        # Immediately restore background audio asynchronously
        threading.Thread(target=self.ducker.stop_ducking, daemon=True, name="FlowPilot-DuckerStop").start()

        def process_worker(active_session: DictationSession, stop_action_time: float):
            try:
                # 1. Stop recorder and get audio data
                t_cap_start = time.perf_counter()
                wav_bytes = self.recorder.stop_recording()
                audio_array = self.recorder.get_last_audio_array()
                t_cap_end = time.perf_counter()

                with self._state_lock:
                    if active_session.is_cancelled or active_session != self._current_session:
                        print(f"[Orchestrator] Session {active_session.session_id} cancelled during capture shutdown. Aborting.")
                        return

                if not wav_bytes:
                    print("[Orchestrator] Dictation was too brief or empty.")
                    with self._state_lock:
                        active_session.transition_to(SessionState.IDLE)
                        self.state = AppState.IDLE
                        self.is_processing = False
                    self._notify(AppState.IDLE, {"notice": "Audio too short."})
                    return

                active_session.audio_bytes = wav_bytes
                active_session.audio_array = audio_array
                t_audio_finalized = time.perf_counter()

                # 2. Transition to TRANSCRIBING
                with self._state_lock:
                    if active_session.is_cancelled or active_session != self._current_session:
                        print(f"[Orchestrator] Session {active_session.session_id} cancelled before STT. Aborting.")
                        return
                    active_session.transition_to(SessionState.TRANSCRIBING)
                    self.state = AppState.TRANSCRIBING
                self._notify(AppState.TRANSCRIBING, {"session_id": active_session.session_id})

                # 3. Transcribe audio (STT) - pass zero-copy float32 array if available
                t_stt_start = time.perf_counter()
                stt_input = audio_array if audio_array is not None else wav_bytes
                stt_task = getattr(active_session, "task", "transcribe")
                stt_lang = getattr(active_session, "language", self.config.get("language", "auto"))
                from engine.context_processor import ProfileResolver
                stt_profile = ProfileResolver.resolve(self.config, active_session.target_window_info, active_session.tone_mode)
                stt_result = self.stt.transcribe(stt_input, task=stt_task, language=stt_lang, profile=stt_profile)
                t_stt_end = time.perf_counter()

                with self._state_lock:
                    if active_session.is_cancelled or active_session != self._current_session:
                        print(f"[Orchestrator] Session {active_session.session_id} cancelled during/after STT. Aborting.")
                        return

                raw_text = stt_result.get("text", "")
                detected_lang = stt_result.get("detected_language", "unknown")
                active_session.raw_text = raw_text
                active_session.detected_language = detected_lang
                stt_duration = round(t_stt_end - t_stt_start, 3)
                print(f"[Orchestrator] STT completed ({stt_duration}s, task={stt_task}, lang={detected_lang}, chars={len(raw_text)}).")

                if not raw_text or not raw_text.strip():
                    with self._state_lock:
                        active_session.transition_to(SessionState.IDLE)
                        self.state = AppState.IDLE
                        self.is_processing = False
                    self._notify(AppState.IDLE, {"notice": "No speech detected."})
                    return

                # 4. Transition to VALIDATING / Context Processing
                with self._state_lock:
                    if active_session.is_cancelled or active_session != self._current_session:
                        print(f"[Orchestrator] Session {active_session.session_id} cancelled before validation. Aborting.")
                        return
                    active_session.transition_to(SessionState.VALIDATING)
                    self.state = AppState.VALIDATING
                self._notify(AppState.VALIDATING, {"char_count": len(raw_text), "session_id": active_session.session_id})

                # Post-process via ContextProcessor (using English formatting if translated, or detected language if original)
                t_clean_start = time.perf_counter()
                format_lang = "en" if stt_task == "translate" else detected_lang

                target_hwnd = active_session.target_window_info.get("hwnd") if active_session.target_window_info else None
                preceding_text, following_text = None, None
                if target_hwnd:
                    try:
                        preceding_text, following_text = TextInjector.get_caret_surrounding_text(target_hwnd)
                    except Exception as e:
                        logger.debug("Failed to query caret context: %s", e)

                formatted_text = self.processor.process(
                    raw_text,
                    active_session.target_window_info,
                    session_mode=active_session.tone_mode,
                    language=format_lang,
                    preceding_text=preceding_text,
                    following_text=following_text
                )
                if self.personalization:
                    expanded_text, trigger = self.personalization.expand_snippets(formatted_text)
                    if trigger:
                        print("[Orchestrator] Expanded voice snippet trigger matched.")
                        formatted_text = expanded_text
                # 4b. Optional Tier 2 Local Text Repair (process-isolated SLM sandbox)
                if self.text_repair is not None and self.config.get("local_text_repair_enabled", False):
                    try:
                        t_repair_start = time.perf_counter()
                        repair_res = self.text_repair.repair(formatted_text, language=format_lang)
                        t_repair_end = time.perf_counter()
                        repair_ms = round((t_repair_end - t_repair_start) * 1000, 2)
                        active_session.record_timing("local_repair_ms", repair_ms)
                        logger.info(
                            "LocalTextRepair finished: %s (%.2f ms, fallback=%s)",
                            repair_res.status.value,
                            repair_ms,
                            repair_res.fallback_used
                        )
                        formatted_text = repair_res.text
                    except Exception as e:
                        logger.warning("LocalTextRepair execution failed, retaining Whisper text: %s", e)

                t_clean_end = time.perf_counter()
                format_duration = round(t_clean_end - t_clean_start, 3)
                active_session.candidate_text = formatted_text
                active_session.final_text = formatted_text
                print(f"[Orchestrator] Formatting completed ({format_duration}s, chars={len(formatted_text)}).")

                # 5. Transition to INJECTING
                with self._state_lock:
                    if active_session.is_cancelled or active_session != self._current_session:
                        print(f"[Orchestrator] Session {active_session.session_id} cancelled before injection. Aborting.")
                        return
                    active_session.transition_to(SessionState.INJECTING)
                    self.state = AppState.INSERTING_TEXT
                self._notify(AppState.INSERTING_TEXT, {"char_count": len(formatted_text), "session_id": active_session.session_id})

                # Inject formatted text into target window with confirmed fallback and truthful status
                t_inj_start = time.perf_counter()
                target_hwnd = active_session.target_window_info.get("hwnd")
                injection_method = "clipboard_paste"
                from engine.text_injector import InjectionStatus, InjectionResult
                if getattr(active_session, "is_selection_rewrite", False) and getattr(active_session, "selected_text", None):
                    print("[Orchestrator] Executing in-place selection rewrite via SelectionRewriter...")
                    rewrite_res = self.selection_rewriter.process_and_rewrite(
                        formatted_text,
                        selected_text=active_session.selected_text,
                        target_hwnd=target_hwnd
                    )
                    if rewrite_res.status == "applied":
                        success = True
                        inj_res = InjectionResult(
                            status=InjectionStatus.CONFIRMED_INSERTED,
                            chars_sent=len(rewrite_res.replacement_text),
                            target_hwnd=target_hwnd
                        )
                        formatted_text = rewrite_res.replacement_text
                        self._notify(AppState.SUCCESS, {
                            "notice": f"Replaced selection ({rewrite_res.intent})",
                            "can_undo": True,
                            "undo_hotkey": "Alt+Shift+U"
                        })
                    else:
                        success = False
                        inj_res = InjectionResult(
                            status=InjectionStatus.FAILED_RECOVERY_AVAILABLE,
                            target_hwnd=target_hwnd,
                            error_message=rewrite_res.error_message or "Rewrite blocked"
                        )
                        self._notify(AppState.ERROR, {
                            "notice": rewrite_res.error_message or "Selection rewrite failed",
                            "message": rewrite_res.error_message
                        })
                else:
                    inj_res = TextInjector.inject_with_status(formatted_text, target_hwnd, verify_confirmation=True)
                success = bool(inj_res)
                if not success and inj_res.status != InjectionStatus.FAILED_RECOVERY_AVAILABLE:
                    print("[Orchestrator] Standard clipboard paste failed. Falling back to direct SendInput Unicode typing...")
                    injection_method = "sendinput_unicode"
                    typed_ok = TextInjector.inject_unicode_sendinput(formatted_text, target_hwnd)
                    if typed_ok:
                        inj_res = InjectionResult(status=InjectionStatus.SENT_UNVERIFIED, chars_sent=len(formatted_text), target_hwnd=target_hwnd)
                        success = True
                t_inj_end = time.perf_counter()
                active_session.injection_method = injection_method
                active_session.injection_success = success
                if success and target_hwnd:
                    self._schedule_correction_check(target_hwnd, formatted_text)

                # Stage-level high-precision timing calculations
                user_stop_to_cap_ms = round((t_cap_end - stop_action_time) * 1000, 2)
                cap_to_finalize_ms = round((t_audio_finalized - t_cap_end) * 1000, 2)
                finalize_to_stt_ms = round((t_stt_start - t_audio_finalized) * 1000, 2)
                stt_ms = round((t_stt_end - t_stt_start) * 1000, 2)
                cleanup_ms = round((t_clean_end - t_clean_start) * 1000, 2)
                inj_ms = round((t_inj_end - t_inj_start) * 1000, 2)
                delivery_timing = injection_completion_timing(
                    stop_action_time, t_inj_end, self._last_speech_perf
                )

                active_session.record_timing("user_stop_to_cap_ms", user_stop_to_cap_ms)
                active_session.record_timing("cap_to_finalize_ms", cap_to_finalize_ms)
                active_session.record_timing("finalize_to_stt_ms", finalize_to_stt_ms)
                active_session.record_timing("stt_ms", stt_ms)
                active_session.record_timing("cleanup_ms", cleanup_ms)
                active_session.record_timing("inj_ms", inj_ms)
                active_session.record_timing(
                    "stop_to_injection_result_ms",
                    delivery_timing["stop_action_to_injection_result_ms"],
                )

                self.last_pipeline_timing = {
                    "stop_to_capture_shutdown_ms": user_stop_to_cap_ms,
                    "capture_to_audio_finalization_ms": cap_to_finalize_ms,
                    "audio_finalization_to_stt_start_ms": finalize_to_stt_ms,
                    "transcription_ms": stt_ms,
                    "cleanup_ms": cleanup_ms,
                    "text_insertion_ms": inj_ms,
                    **delivery_timing,
                }

                print(
                    f"[Latency Breakdown] Stop->Cap: {user_stop_to_cap_ms}ms | Finalize: {cap_to_finalize_ms}ms | "
                    f"STT: {stt_ms}ms | Clean: {cleanup_ms}ms | Inject: {inj_ms}ms | "
                    f"StopAction->InjectionResult: {delivery_timing['stop_action_to_injection_result_ms']}ms"
                    + (
                        f" | AcousticEnd->InjectionResult: {delivery_timing['acoustic_end_to_injection_result_ms']}ms"
                        if delivery_timing["acoustic_end_to_injection_result_ms"] is not None else ""
                    )
                )

                # 6. Save into history and recovery buffer
                total_duration = round(time.time() - active_session.created_at, 2)
                save_text = self.config.get("save_history_text") is True
                history_entry = {
                    "id": int(time.time() * 1000),
                    "session_id": active_session.session_id,
                    "raw_text": raw_text if save_text else "",
                    "formatted_text": formatted_text if save_text else "",
                    "target_app": active_session.target_window_info.get("process_name"),
                    "language": detected_lang,
                    "duration_sec": total_duration,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "injection_status": inj_res.status.value,
                    "injection_confirmed": inj_res.is_confirmed(),
                    "injection_method": injection_method
                }
                # Keep active formatted_text and raw_text in volatile memory for Tray 'Copy Last Dictation'
                self.last_dictation = {
                    **history_entry,
                    "formatted_text": formatted_text,
                    "raw_text": raw_text
                }

                telemetry_event = {
                    "timestamp": time.time(),
                    "session_id": active_session.session_id,
                    "datetime": history_entry["timestamp"],
                    "target_app": history_entry["target_app"],
                    "audio_duration_sec": round(len(wav_bytes) / 32000.0, 2),
                    "stt_duration_sec": stt_duration,
                    "format_duration_sec": format_duration,
                    "total_duration_sec": total_duration,
                    **delivery_timing,
                    "char_count": len(formatted_text),
                    "injection_method": injection_method,
                    "injection_status": inj_res.status.value,
                    "injection_confirmed": inj_res.is_confirmed(),
                    "injection_success": success
                }
                self._persist_completed_dictation(
                    enabled=save_text,
                    history_entry=history_entry,
                    raw_text=raw_text,
                    formatted_text=formatted_text,
                    wav_bytes=wav_bytes,
                    duration_sec=total_duration,
                    language=detected_lang,
                    session=active_session,
                    telemetry_event=telemetry_event,
                )

                if not success or inj_res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE:
                    err_msg = inj_res.error_message or "Paste failed; text held for recovery"
                    print(f"[Orchestrator Warning] {err_msg}")
                    TextInjector.last_injected_text = formatted_text
                    with self._state_lock:
                        active_session.transition_to(SessionState.ERROR)
                        self.state = AppState.ERROR
                        self.is_processing = False
                    self.feedback.play_error()
                    self._notify(AppState.ERROR, {
                        "message": err_msg,
                        "notice": "Text held in recovery. Shift+Alt+X copies it.",
                        "session_id": active_session.session_id,
                        "recovery_available": True
                    })
                    time.sleep(2.0)
                    with self._state_lock:
                        if self.state == AppState.ERROR:
                            self.state = AppState.IDLE
                            self._notify(AppState.IDLE)
                    return

                # 7. Transition to SUCCESS with truthful confirmation reporting
                confirmed = inj_res.is_confirmed()
                notice_msg = "Inserted & confirmed" if confirmed else "Sent — unverified target (please check)"
                with self._state_lock:
                    active_session.transition_to(SessionState.SUCCESS)
                    self.state = AppState.SUCCESS
                    self.is_processing = False
                    self._success_generation += 1
                    success_generation = self._success_generation
                    self._notify(AppState.SUCCESS, {
                        "text": formatted_text,
                        "total_duration": total_duration,
                        "history_entry": history_entry,
                        "session_id": active_session.session_id,
                        "injection_status": inj_res.status.value,
                        "injection_confirmed": confirmed,
                        "notice": notice_msg
                    })

                # Show status briefly (0.8s), then transition to IDLE
                time.sleep(0.8)
                with self._state_lock:
                    if (self.state == AppState.SUCCESS
                            and self._success_generation == success_generation
                            and active_session == self._current_session):
                        active_session.transition_to(SessionState.IDLE)
                        self.state = AppState.IDLE
                        self._notify(AppState.IDLE)

            except Exception as e:
                print(f"[Orchestrator Error] Processing failed: {e}")
                with self._state_lock:
                    active_session.transition_to(SessionState.ERROR)
                    self.state = AppState.ERROR
                    self.is_processing = False
                self._notify(AppState.ERROR, {"message": str(e), "session_id": active_session.session_id})
                time.sleep(2.0)
                with self._state_lock:
                    if self.state == AppState.ERROR:
                        self.state = AppState.IDLE
                        self._notify(AppState.IDLE)
            finally:
                # Ensure audio ducking is always cleanly restored
                try:
                    self.ducker.stop_ducking()
                except Exception:
                    pass
                self._apply_pending_model_switch_if_idle()

        threading.Thread(target=process_worker, args=(session, t_stop_action), daemon=True, name="FlowPilot-Processor").start()

    def toggle_dictation(self, translation_mode: Optional[bool] = None):
        # Hold-to-Toggle Latching: If recording was initiated via push-to-talk,
        # tapping toggle latches into hands-free mode without stopping recording.
        tap_latch = getattr(self, "_tap_latch", None)
        if tap_latch and hasattr(tap_latch, "latch_to_toggle") and tap_latch.state == getattr(tap_latch, "HELD", None):
            if self._tap_latch.latch_to_toggle():
                print("[Orchestrator] Hold-to-Toggle latching activated: switched to hands-free recording.")
                return

        with self._state_lock:
            cur = self.state

        if cur == AppState.IDLE:
            self.start_dictation(translation_mode=translation_mode)
        elif cur == AppState.STARTING_RECORDING:
            with self._state_lock:
                self._stop_pending = True
            print("[Orchestrator] Stop queued while starting recording.")
        elif cur == AppState.RECORDING:
            self.stop_dictation_and_process()
        elif cur in (AppState.STOPPING_RECORDING, AppState.TRANSCRIBING, AppState.VALIDATING, AppState.INSERTING_TEXT):
            print(f"[Orchestrator] Shortcut pressed while {cur}. Displaying progress notification.")
            self._notify(cur, {"notice": "Processing dictation. Please wait..."})
        elif cur == AppState.SUCCESS:
            self.start_dictation(translation_mode=translation_mode)
        elif cur in (AppState.ERROR, AppState.CANCELLED):
            self.start_dictation(translation_mode=translation_mode)

    def _apply_pending_model_switch_if_idle(self):
        with self._state_lock:
            if self.state != AppState.IDLE or not self._pending_model_switch:
                return
            target_model = self._pending_model_switch
            self._pending_model_switch = None
        print(f"[Orchestrator] Applying deferred model switch to '{target_model}'...")
        self.update_config({"local_model_size": target_model})

    def update_config(self, new_config: Dict[str, Any]):
        if OBSOLETE_CLOUD_KEYS.intersection(new_config) or new_config.get("engine_mode", "local") != "local":
            logger.warning("Unsupported cloud speech setting refused")
            return False
        old_hk = self.config.get("hotkey")
        old_mode = self.config.get("hotkey_mode")
        old_exclusive = self.config.get("hotkey_exclusive", False)
        old_mute_enabled = bool(self.config.get("hold_to_mute_enabled", False))
        old_mute_hotkey = self.config.get("mute_hotkey", "Ctrl+Space")
        old_model = self.config.get("local_model_size", "base")
        new_model = new_config.get("local_model_size")
        model_changed = (new_model is not None and new_model != old_model)

        updated_config = local_only_config({**self.config, **new_config})
        mute_enabled = bool(updated_config.get("hold_to_mute_enabled", False))
        mute_hotkey = str(updated_config.get("mute_hotkey", "Ctrl+Space")).strip()
        if mute_enabled:
            try:
                mute_mods, mute_vk = parse_hotkey_string(mute_hotkey)
                dictation_mods, dictation_vk = parse_hotkey_string(updated_config.get("hotkey", "Ctrl+Shift+Space"))
                if not mute_mods:
                    print("[Orchestrator Warning] Hold-to-mute requires a modifier shortcut; bare keys are rejected.")
                    return False
                if (mute_mods, mute_vk) == (dictation_mods, dictation_vk):
                    print("[Orchestrator Warning] Hold-to-mute cannot reuse the dictation shortcut.")
                    return False
                mute_conflict = dictation_hotkey_conflict(mute_hotkey)
                if mute_conflict:
                    print(f"[Orchestrator Warning] Hold-to-mute shortcut conflicts with {mute_conflict}.")
                    return False
            except ValueError as exc:
                print(f"[Orchestrator Warning] Invalid hold-to-mute shortcut: {exc}")
                return False
        new_hk = updated_config.get("hotkey", "Ctrl+Shift+Space")
        if new_hk != old_hk:
            updated_config["hotkey_exclusive"] = True
            try:
                parse_hotkey_string(new_hk)
                conflict = dictation_hotkey_conflict(new_hk)
                if conflict:
                    print(f"[Orchestrator Warning] Dictation shortcut conflicts with {conflict}.")
                    return False
            except ValueError as exc:
                print(f"[Orchestrator Warning] Invalid dictation shortcut: {exc}")
                return False
            current_hk = old_hk if self.hotkey_service.is_alive() else None
            available, reason = Win32HotkeyService.test_hotkey_availability(new_hk, currently_active_hotkey=current_hk)
            if not available:
                print(f"[Orchestrator Warning] Dictation shortcut unavailable: {reason}")
                return False

        if model_changed:
            with self._state_lock:
                in_flight = self.state in (
                    AppState.RECORDING,
                    AppState.STARTING_RECORDING,
                    AppState.STOPPING_RECORDING,
                    AppState.TRANSCRIBING,
                    AppState.VALIDATING,
                    AppState.INSERTING_TEXT
                )
            if in_flight:
                print(f"[Orchestrator] Model switch to '{new_model}' deferred until in-flight dictation completes.")
                self._pending_model_switch = new_model
                updated_config["local_model_size"] = old_model
            else:
                # Idle: validate and load new model before committing config
                try:
                    test_cfg = {**self.config, "local_model_size": new_model}
                    self.stt.config = test_cfg
                    self.stt._get_local_model()
                except Exception as e:
                    print(f"[Orchestrator Warning] Failed to switch to model '{new_model}': {e}")
                    self.stt.config = self.config
                    return False

        # Persist identity in the same transaction as the rest of the settings.
        if "audio_input_selection" not in new_config:
            if "audio_device_index" in new_config or "mic_device" in new_config:
                requested = new_config.get("audio_device_index", new_config.get("mic_device"))
                updated_config["audio_input_selection"] = build_device_selection(requested)
            else:
                migrate_legacy_audio_config(updated_config)
        resolution = resolve_audio_input(updated_config["audio_input_selection"])
        updated_config["audio_device_index"] = resolution.device_index
        if not save_config(updated_config):
            return False
        self.config = updated_config
        # Update submodules
        self.stt.config = self.config
        self.processor.config = self.config

        # Update audio input device dynamically if changed
        old_dev = getattr(self.recorder, "device", None)
        self._device_selection = self.config["audio_input_selection"]
        self._last_device_resolution = resolution
        new_dev = resolution.device_index

        if new_dev != old_dev or getattr(self.recorder, "_device_change_pending", False):
            print(f"[Orchestrator] Audio input device changed ({old_dev} -> {new_dev}). Updating recorder.")
            self.recorder.set_device(new_dev, defer_if_recording=True)

        print("[Orchestrator] Configuration updated.")

        # Re-bind hotkeys dynamically if shortcut or mode changed
        new_hk = self.config.get("hotkey")
        new_mode = self.config.get("hotkey_mode")
        new_exclusive = self.config.get("hotkey_exclusive", False)
        new_mute_enabled = bool(self.config.get("hold_to_mute_enabled", False))
        new_mute_hotkey = self.config.get("mute_hotkey", "Ctrl+Space")
        if ((new_hk and new_hk != old_hk) or (new_mode and new_mode != old_mode)
                or new_exclusive != old_exclusive
                or new_mute_enabled != old_mute_enabled
                or new_mute_hotkey != old_mute_hotkey):
            print(f"[Orchestrator] Re-registering hotkey service with updated shortcut '{new_hk}' (mode={new_mode})...")
            self.stop_hotkey_listener()
            from engine.hotkey_service import get_hotkey_service
            self.hotkey_service = get_hotkey_service()
            self.start_hotkey_listener()
        return True

    def _set_recording_muted(self, muted: bool):
        """Apply a temporary capture mute without ending the active session."""
        setter = getattr(self.recorder, "set_muted", None)
        if not callable(setter):
            return False
        active = bool(getattr(self.recorder, "is_recording", False))
        if not active:
            return False
        setter(bool(muted))
        is_muted = bool(getattr(self.recorder, "is_muted", False))
        self._notify(AppState.RECORDING, {
            "is_muted": is_muted,
            "notice": "Microphone muted" if is_muted else "Microphone resumed",
        })
        return is_muted

    def undo_last_rewrite(self) -> bool:
        """Rolls back the last in-place selection rewrite transaction via SelectionRewriter."""
        if hasattr(self, "selection_rewriter"):
            success = self.selection_rewriter.undo_last_rewrite()
            if success:
                self._notify(AppState.IDLE, {
                    "notice": "Reverted last text rewrite",
                    "recovery_action": True
                })
            else:
                self._notify(AppState.IDLE, {
                    "notice": "Nothing to undo",
                    "recovery_action": True
                })
            return success
        return False

    def re_copy_last(self) -> bool:
        """Copies the last dictation text directly to clipboard with UI feedback."""
        success = TextInjector.re_copy_last()
        text = TextInjector.last_injected_text or (self.last_dictation.get("formatted_text") if isinstance(self.last_dictation, dict) else "")
        with self._state_lock:
            current_state = self.state
        active = current_state in (
            AppState.STARTING_RECORDING, AppState.RECORDING,
            AppState.STOPPING_RECORDING, AppState.TRANSCRIBING,
            AppState.VALIDATING, AppState.INSERTING_TEXT,
        )
        if success:
            # Clipboard copy is not another successful paste. Use neutral idle
            # feedback outside an active session so an earlier unverified paste
            # cannot be relabelled as confirmed by the UI's default.
            self._notify(current_state if active else AppState.IDLE, {
                "notice": "Copied last dictation to clipboard",
                "text": text,
                "recovery_action": True,
            })
        else:
            self._notify(current_state if active else AppState.ERROR, {
                "message": "No previous dictation text found in clipboard recovery buffer.",
                "notice": "No previous dictation to copy",
                "recovery_action": True,
            })
        return success

    def re_inject_last(self):
        """
        Re-injects the last dictation text into the currently active or last target window.
        Returns the structured InjectionResult (CONFIRMED_INSERTED, SENT_UNVERIFIED,
        FAILED_RECOVERY_AVAILABLE, or ERROR) and notifies UI/HUD.
        """
        from engine.text_injector import InjectionStatus, InjectionResult
        with self._state_lock:
            if self.state in (
                AppState.RECORDING, AppState.STARTING_RECORDING,
                AppState.STOPPING_RECORDING, AppState.TRANSCRIBING,
                AppState.VALIDATING, AppState.INSERTING_TEXT,
            ):
                res = InjectionResult(
                    status=InjectionStatus.ERROR,
                    error_message="Cannot re-inject while dictation is in progress.",
                    recovery_available=False
                )
                self._notify(self.state, {
                    "message": res.error_message,
                    "notice": "Dictation in progress — recovery postponed",
                })
                return res

            # Keep the state lock through target resolution and dispatch. A new
            # dictation must not start while a recovery paste is in flight.
            text = TextInjector.last_injected_text
            if not text:
                res = InjectionResult(
                    status=InjectionStatus.ERROR,
                    error_message="No previous dictation text found in recovery buffer.",
                    recovery_available=False,
                )
                self._notify(AppState.ERROR, {
                    "message": res.error_message,
                    "notice": "No previous dictation found to re-insert",
                    "recovery_action": True,
                })
                return res

            cur_info = WindowInspector.get_active_window_info()
            cur_hwnd = cur_info.get("hwnd", 0)
            target = cur_hwnd if (cur_hwnd and not TextInjector._is_flowpilot_window(cur_hwnd)) else (self.target_window_info.get("hwnd") or TextInjector.last_target_hwnd)
            res = TextInjector.inject_last(target_hwnd=target)
            if isinstance(self.last_dictation, dict) and "injection_status" in self.last_dictation:
                self.last_dictation["prior_injection_status"] = self.last_dictation.get("injection_status")
                self.last_dictation["injection_status"] = res.status.value

            if res.status in (InjectionStatus.ERROR, InjectionStatus.FAILED_RECOVERY_AVAILABLE):
                self._notify(AppState.ERROR, {
                    "message": res.error_message or "Could not re-insert text",
                    "notice": ("Text kept for manual recovery" if res.recovery_available
                               else "Re-insertion failed"),
                    "injection_status": res.status.value,
                    "recovery_action": True,
                })
                return res

            confirmed = res.is_confirmed()
            self._success_generation += 1
            generation = self._success_generation
            self.state = AppState.SUCCESS
            self._notify(AppState.SUCCESS, {
                "text": text,
                "injection_status": res.status.value,
                "injection_confirmed": confirmed,
                "notice": ("Re-inserted & confirmed" if confirmed
                           else "Re-sent — unverified target (please check)"),
                "recovery_action": True,
            })

        def _reset_idle():
            time.sleep(0.8)
            with self._state_lock:
                if self.state == AppState.SUCCESS and self._success_generation == generation:
                    self.state = AppState.IDLE
                    self._notify(AppState.IDLE)
        threading.Thread(target=_reset_idle, daemon=True).start()
        return res

    def start_hotkey_listener(self):
        """
        Registers native Win32 global hotkeys using RegisterHotKey.
        Supports both Toggle Mode and Push-to-Talk Mode.
        Existing profiles retain the former aliases until the user explicitly
        chooses a shortcut. After that, only their chosen key controls dictation.
        Auxiliary actions retain their dedicated shortcuts across changes.
        """
        try:
            from engine.hotkey_service import TapLatch
            if self.hotkey_service.is_alive():
                return
            self._tap_latch = TapLatch(
                on_start=self.start_dictation,
                on_stop=self.stop_dictation_and_process,
                window_ms=350
            )

            primary_hk = self.config.get("hotkey", "Ctrl+Shift+Space")
            clean_hk = primary_hk.replace("<", "").replace(">", "").strip()
            mode = self.config.get("hotkey_mode", "toggle")
            parse_hotkey_string(clean_hk)
            conflict = dictation_hotkey_conflict(clean_hk)
            if conflict:
                raise ValueError(f"Dictation shortcut conflicts with {conflict}.")

            if mode == "push_to_talk":
                # Push-to-talk with TapLatch double-tap hands-free support
                self.hotkey_service.register(clean_hk, self._tap_latch.press, on_release=self._tap_latch.release)
            else:
                # Toggle: press once to start, press again to stop
                self.hotkey_service.register(clean_hk, self.toggle_dictation)

            if not self.config.get("hotkey_exclusive", False):
                # Backward compatibility: do not silently remove F9 from an
                # existing installation before its owner visits Settings.
                primary_code = parse_hotkey_string(clean_hk)
                if primary_code != parse_hotkey_string("F9"):
                    if mode == "push_to_talk":
                        self.hotkey_service.register("F9", self._tap_latch.press, on_release=self._tap_latch.release)
                    else:
                        self.hotkey_service.register("F9", self.toggle_dictation)
                if primary_code != parse_hotkey_string("Ctrl+Alt+Space"):
                    self.hotkey_service.register("Ctrl+Alt+Space", self.toggle_dictation)

            for shortcut, callback in self._auxiliary_hotkeys.items():
                self.hotkey_service.register(shortcut, callback)

            if self.config.get("hold_to_mute_enabled", False):
                mute_shortcut = self.config.get("mute_hotkey", "Ctrl+Space")
                self.hotkey_service.register(
                    mute_shortcut,
                    lambda: self._set_recording_muted(True),
                    on_release=lambda: self._set_recording_muted(False),
                )
                self._mute_hotkey_registered = True
            else:
                self._mute_hotkey_registered = False

            # Register Alt+Shift+Z (Paste Last) and Alt+Shift+X (Copy Last) for instant recovery (Wispr Flow alignment)
            try:
                self.hotkey_service.register("Alt+Shift+Z", self.re_inject_last)
            except Exception:
                pass
            try:
                self.hotkey_service.register("Alt+Shift+X", self.re_copy_last)
            except Exception:
                pass
            try:
                self.hotkey_service.register("Alt+Shift+U", self.undo_last_rewrite)
            except Exception:
                pass

            success = self.hotkey_service.start(timeout=3.0)
            service_name = self.hotkey_service.__class__.__name__
            if success:
                print(f"[Orchestrator] {service_name} active: '{clean_hk}' (mode={mode}), auxiliary and recovery shortcuts")
            if self.hotkey_service.stats['errors']:
                err_summary = "; ".join(self.hotkey_service.stats['errors'])
                print(f"[Orchestrator Warning] {service_name} encountered errors: {err_summary}")
                self._notify(AppState.ERROR, {
                    "message": f"Hotkey conflict: {err_summary}",
                    "notice": "Shortcut already in use by another app"
                })
        except Exception as e:
            print(f"[Orchestrator Error] Failed to start hotkey service: {e}")

    def stop_hotkey_listener(self):
        """
        Unregisters all native Win32 hotkeys and terminates the message loop cleanly.
        """
        if self.hotkey_service:
            self.hotkey_service.stop()
            print("[Orchestrator] Hotkey service stopped.")

    def add_auxiliary_hotkey(self, shortcut: str, callback: Callable[[], None]):
        """Keep a desktop action bound across dictation shortcut changes."""
        if self.hotkey_service.is_alive():
            raise RuntimeError("Register auxiliary hotkeys before starting the listener.")
        self._auxiliary_hotkeys[shortcut] = callback

    def stop(self):
        """Clean shutdown of all orchestrator services."""
        self._capture_watchdog_stop.set()
        self.stop_hotkey_listener()
        if self.text_repair is not None:
            try:
                self.text_repair.shutdown()
            except Exception as e:
                logger.warning("LocalTextRepair shutdown error: %s", e)
        try:
            self.ducker.stop_ducking()
        except Exception:
            pass
        try:
            self.recorder.close()
        except Exception:
            pass

    def _persist_completed_dictation(
        self,
        *,
        enabled: bool,
        history_entry: Dict[str, Any],
        raw_text: str,
        formatted_text: str,
        wav_bytes: bytes,
        duration_sec: float,
        language: str,
        session: DictationSession,
        telemetry_event: Dict[str, Any],
    ) -> None:
        """Persist dictation data only when the user explicitly enables history.

        Never-store mode keeps the recovery buffer in memory but performs no
        dictation-related disk writes, including insights or pilot metrics.
        """
        if not enabled:
            return

        try:
            from engine.insights_engine import get_insights_engine
            target_proc = session.target_window_info.get("process_name") or "Desktop"
            get_insights_engine().record_dictation(formatted_text, duration_sec, str(target_proc))
        except Exception as _ie_err:
            print(f"[Orchestrator Warning] Insights recording deferred: {_ie_err}")

        try:
            from engine.history_vault import get_history_vault
            get_history_vault().record_dictation(
                formatted_text=formatted_text,
                raw_text=raw_text,
                target_app=str(session.target_window_info.get("process_name") or "Desktop"),
                duration_sec=duration_sec,
                audio_bytes=wav_bytes,
                language=language,
                session_id=session.session_id,
            )
        except Exception as _hv_err:
            print(f"[Orchestrator Warning] History Vault recording deferred: {_hv_err}")

        self._record_telemetry(telemetry_event)
        history = self.config.get("history", [])
        history.insert(0, history_entry)
        self.config["history"] = history[:50]
        save_config(self.config)

    def _record_telemetry(self, data: Dict[str, Any]):
        """Records bounded, opt-in local metadata for pilot metrics."""
        if not self.config.get("telemetry_enabled", False):
            return
        try:
            append_local_event(data, Path.home() / ".flowpilot")
        except Exception as exc:
            logger.warning("Could not write opt-in pilot metrics: %s", exc)
