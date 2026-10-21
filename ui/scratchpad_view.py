"""
FlowPilot In-App Voice Scratchpad Canvas (PR 4)
A native drafting workspace with:
- Live voice dictation directly into the editor cursor
- Bounded voice-directed text editing ("replace Friday with Monday", "remove this part", "add ... at the end")
- Atomic EditTransaction planning, diff preview, and verified apply
- Verified undo transactions tied to document revision
- Word and character count telemetry
- One-click markdown formatting, copy-all, and export
- Persistent local auto-save
"""

import logging
from pathlib import Path
import uuid
from typing import Optional, Callable, Tuple, Any

logger = logging.getLogger("FlowPilot.Scratchpad")

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QFont, QTextCursor, QColor
import pyperclip

from engine.voice_editor import get_voice_editor, VoiceEditor, EditTransaction
from engine.config import get_config_file

AUTOSAVE_FILE = get_config_file().parent / "scratchpad_autosave.txt"


def _python_selection(text, cursor):
    """Qt cursor offsets are UTF-16 units, not Python Unicode offsets."""
    encoded = text.encode("utf-16-le")
    return tuple(len(encoded[:offset * 2].decode("utf-16-le"))
                 for offset in (cursor.selectionStart(), cursor.selectionEnd()))


class VoiceCommandWorker(QThread):
    """Background worker executing ASR decode and LLM transform off the UI thread."""
    command_planned = Signal(int, str, object, str)  # (request_id, cleaned_instruction, tx, error_msg)
    status_updated = Signal(int, str)                # (request_id, status_msg)

    def __init__(self, stt, editor, doc_text, sel_range, audio, target_id: str = "scratchpad:editor", request_id: int = 0, parent=None):
        super().__init__(parent)
        self.stt = stt
        self.editor = editor
        self.doc_text = doc_text
        self.sel_range = sel_range
        self.audio = audio
        self.target_id = target_id
        self.request_id = request_id
        self._cancelled = False
        import threading
        self._lock = threading.Lock()

    def cancel(self):
        with self._lock:
            self._cancelled = True

    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

    def run(self):
        if self.is_cancelled():
            return
        try:
            self.status_updated.emit(self.request_id, "Transcribing voice command...")
            res = self.stt.transcribe(self.audio)
            if self.is_cancelled():
                return

            raw = res.get("text", "").strip() if isinstance(res, dict) else str(res).strip()
            if not raw:
                if not self.is_cancelled():
                    self.command_planned.emit(self.request_id, "", None, "No clear speech recognized. Please repeat the command.")
                return

            cleaned = raw.rstrip(".!? ")
            if self.is_cancelled():
                return

            self.status_updated.emit(self.request_id, "Planning voice edit...")
            start, end = self.sel_range if self.sel_range else (0, 0)
            has_sel = (start != end and 0 <= start < end <= len(self.doc_text))
            tx = self.editor.plan_edit(
                document_text=self.doc_text,
                instruction=cleaned,
                selected_range=(start, end) if has_sel else (0, 0),
                target_id=self.target_id,
                target_type="scratchpad"
            )
            if self.is_cancelled():
                return
            self.command_planned.emit(self.request_id, cleaned, tx, "")
        except Exception as e:
            if not self.is_cancelled():
                self.command_planned.emit(self.request_id, "", None, f"Command execution failed: {e}")


class ScratchpadView(QWidget):
    dictate_requested = Signal()
    command_planned = Signal(object)  # Emits EditTransaction when planned via voice

    def __init__(
        self,
        parent=None,
        on_dictate_toggle: Optional[Callable[[], None]] = None,
        stt_engine: Optional[Any] = None,
        audio_recorder: Optional[Any] = None
    ):
        super().__init__(parent)
        self.on_dictate_toggle = on_dictate_toggle
        self._stt_engine = stt_engine
        self._audio_recorder = audio_recorder
        self._is_recording_command = False
        self._command_worker: Optional[VoiceCommandWorker] = None
        self._active_request_id = 0
        self.voice_editor: VoiceEditor = get_voice_editor()
        self.active_transaction: Optional[EditTransaction] = None
        self._target_id = f"scratchpad:{uuid.uuid4().hex}"
        self._init_ui()
        self._load_autosave()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header bar
        header = QHBoxLayout()
        header.setSpacing(10)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("Voice Scratchpad")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #F8FAFC;")
        lbl_subtitle = QLabel("Draft notes, dictate continuously, and edit text with bounded voice commands.")
        lbl_subtitle.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_subtitle)
        header.addLayout(title_box)

        header.addStretch()

        # Stats pill
        self.lbl_stats = QLabel("0 words | 0 chars")
        self.lbl_stats.setStyleSheet("""
            background-color: #1E293B;
            color: #38BDF8;
            font-size: 12px;
            font-weight: 600;
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid #334155;
        """)
        header.addWidget(self.lbl_stats)

        layout.addLayout(header)

        # Action Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_dictate = QPushButton("🎤 Dictate into Pad")
        self.btn_dictate.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-weight: bold;
                padding: 7px 16px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self.btn_dictate.clicked.connect(self._on_dictate_clicked)
        toolbar.addWidget(self.btn_dictate)

        self.btn_voice_edit = QPushButton("✏️ Voice Edit")
        self.btn_voice_edit.setStyleSheet("""
            QPushButton {
                background-color: #7C3AED;
                color: #FFFFFF;
                font-weight: bold;
                padding: 7px 14px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #6D28D9;
            }
        """)
        self.btn_voice_edit.clicked.connect(self._toggle_edit_panel)
        toolbar.addWidget(self.btn_voice_edit)

        btn_copy = QPushButton("📋 Copy All")
        btn_copy.setStyleSheet(self._btn_secondary_style())
        btn_copy.clicked.connect(self._copy_all)
        toolbar.addWidget(btn_copy)

        btn_bullets = QPushButton("• Bulletize")
        btn_bullets.setStyleSheet(self._btn_secondary_style())
        btn_bullets.clicked.connect(self._bulletize)
        toolbar.addWidget(btn_bullets)

        btn_export = QPushButton("💾 Export")
        btn_export.setStyleSheet(self._btn_secondary_style())
        btn_export.clicked.connect(self._export_file)
        toolbar.addWidget(btn_export)

        btn_clear = QPushButton("🧹 Clear")
        btn_clear.setStyleSheet(self._btn_secondary_style())
        btn_clear.clicked.connect(self._clear_pad)
        toolbar.addWidget(btn_clear)

        self.btn_undo_clear = QPushButton("↩ Undo Clear")
        self.btn_undo_clear.setVisible(False)
        self.btn_undo_clear.setStyleSheet("""
            QPushButton {
                background-color: #78350F;
                color: #FDE68A;
                font-weight: 600;
                padding: 7px 13px;
                border-radius: 6px;
                border: 1px solid #F59E0B;
            }
            QPushButton:hover {
                background-color: #92400E;
            }
        """)
        self.btn_undo_clear.clicked.connect(self._undo_clear)
        toolbar.addWidget(self.btn_undo_clear)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Voice Editing Panel (Bounded Natural Language Commands)
        self.edit_panel = QFrame()
        self.edit_panel.setVisible(False)
        self.edit_panel.setStyleSheet("""
            QFrame {
                background-color: #1E1B4B;
                border: 1px solid #4338CA;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        panel_vbox = QVBoxLayout(self.edit_panel)
        panel_vbox.setContentsMargins(10, 8, 10, 8)
        panel_vbox.setSpacing(8)

        panel_row1 = QHBoxLayout()
        panel_row1.setSpacing(8)

        self.input_edit_command = QLineEdit()
        self.input_edit_command.setPlaceholderText("Say or type edit command (e.g., 'replace Friday with Monday', 'remove this part', 'add ... at the end')")
        self.input_edit_command.setStyleSheet("""
            QLineEdit {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #6366F1;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
        """)
        self.input_edit_command.returnPressed.connect(self._on_preview_edit)

        self.btn_speak_command = QPushButton("🎙️ Speak Command")
        self.btn_speak_command.setToolTip("Record a spoken voice command (e.g., 'replace Friday with Monday', 'remove this part')")
        self.btn_speak_command.setStyleSheet("""
            QPushButton {
                background-color: #7C3AED;
                color: #FFFFFF;
                font-weight: 600;
                padding: 8px 12px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #6D28D9; }
        """)
        self.btn_speak_command.clicked.connect(self._toggle_command_recording)

        self.btn_preview_edit = QPushButton("Preview Edit")
        self.btn_preview_edit.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5;
                color: #FFFFFF;
                font-weight: 600;
                padding: 8px 14px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #4338CA; }
        """)
        self.btn_preview_edit.clicked.connect(self._on_preview_edit)

        self.btn_apply_edit = QPushButton("Apply Edit")
        self.btn_apply_edit.setEnabled(False)
        self.btn_apply_edit.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #FFFFFF;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #047857; }
            QPushButton:disabled { background-color: #334155; color: #64748B; }
        """)
        self.btn_apply_edit.clicked.connect(self._on_apply_edit)

        self.btn_cancel_edit = QPushButton("✕")
        self.btn_cancel_edit.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #334155; color: #FFFFFF; }
        """)
        self.btn_cancel_edit.clicked.connect(self._cancel_edit)

        panel_row1.addWidget(self.input_edit_command, 4)
        panel_row1.addWidget(self.btn_speak_command, 1)
        panel_row1.addWidget(self.btn_preview_edit, 1)
        panel_row1.addWidget(self.btn_apply_edit, 1)
        panel_row1.addWidget(self.btn_cancel_edit)
        panel_vbox.addLayout(panel_row1)

        self.lbl_edit_diff = QLabel("")
        self.lbl_edit_diff.setWordWrap(True)
        self.lbl_edit_diff.setStyleSheet("font-size: 12px; color: #A5B4FC; font-family: monospace; padding-left: 4px;")
        panel_vbox.addWidget(self.lbl_edit_diff)

        layout.addWidget(self.edit_panel)

        # Text Drafting Canvas
        self.editor = QTextEdit(self)
        self.editor.setPlaceholderText("Start typing, click 'Dictate into Pad' (or F9), or use 'Voice Edit' to transform text...")
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 14px;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-size: 14px;
                line-height: 1.6;
            }
            QTextEdit:focus {
                border: 1px solid #38BDF8;
            }
        """)
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.selectionChanged.connect(self._invalidate_preview)
        self.input_edit_command.textChanged.connect(self._invalidate_preview)
        layout.addWidget(self.editor)

        # Auto-save timer (debounced 1.5s)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._save_autosave)

    def _btn_secondary_style(self) -> str:
        return """
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                font-weight: 600;
                padding: 7px 13px;
                border-radius: 6px;
                border: 1px solid #334155;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #38BDF8;
            }
        """

    def _toggle_edit_panel(self):
        is_visible = self.edit_panel.isVisible()
        self.edit_panel.setVisible(not is_visible)
        if not is_visible:
            self.input_edit_command.setFocus()
            self.input_edit_command.selectAll()

    def _on_preview_edit(self):
        instruction = self.input_edit_command.text().strip()
        if not instruction:
            return

        cursor = self.editor.textCursor()
        doc_text = self.editor.toPlainText()
        sel_range = _python_selection(doc_text, cursor)

        tx = self.voice_editor.plan_edit(
            document_text=doc_text,
            selected_range=sel_range,
            instruction=instruction,
            target_id=self._target_id,
            target_type="scratchpad"
        )
        self.active_transaction = tx

        if tx.can_apply:
            self.lbl_edit_diff.setText(f"✓ Planned: {tx.diff_preview}")
            self.lbl_edit_diff.setStyleSheet("color: #34D399; font-size: 12px; font-family: monospace;")
            self.btn_apply_edit.setEnabled(True)
            self.btn_apply_edit.setFocus()
        else:
            self.lbl_edit_diff.setText(f"⚠ {tx.error_message or tx.diff_preview}")
            self.lbl_edit_diff.setStyleSheet("color: #F87171; font-size: 12px; font-family: monospace;")
            self.btn_apply_edit.setEnabled(False)

    def _on_apply_edit(self):
        if not self.active_transaction or not self.active_transaction.can_apply:
            return

        cursor = self.editor.textCursor()
        doc_text = self.editor.toPlainText()
        sel_range = _python_selection(doc_text, cursor)
        transaction = self.active_transaction

        ok, resulting_text, msg = self.voice_editor.apply_transaction(
            transaction=transaction,
            current_document_text=doc_text,
            current_selection=sel_range,
            current_target_id=self._target_id
        )

        if ok:
            # Preserve cursor near the edited position
            new_cursor_pos = min(len(resulting_text), transaction.selected_range[1])
            self.active_transaction = None
            self.editor.setPlainText(resulting_text)
            new_cursor = self.editor.textCursor()
            new_cursor.setPosition(len(resulting_text[:new_cursor_pos].encode("utf-16-le")) // 2)
            self.editor.setTextCursor(new_cursor)

            self.lbl_edit_diff.setText(f"✓ Applied! (Say 'undo that edit' to revert)")
            self.lbl_edit_diff.setStyleSheet("color: #38BDF8; font-size: 12px; font-family: monospace;")
            self.btn_apply_edit.setEnabled(False)
            self.active_transaction = None
            self._save_autosave()
        else:
            self.lbl_edit_diff.setText(f"✕ Apply failed: {msg}")
            self.lbl_edit_diff.setStyleSheet("color: #EF4444; font-size: 12px; font-family: monospace;")
            self.btn_apply_edit.setEnabled(False)
            self.active_transaction = None

    def execute_voice_command(self, instruction: str, auto_apply: bool = False) -> EditTransaction:
        """
        Executes or plans a voice editing command directly inside the Scratchpad canvas.
        If auto_apply is True and command is unambiguous, applies immediately.
        """
        self.edit_panel.setVisible(True)
        self.input_edit_command.setText(instruction)

        cursor = self.editor.textCursor()
        doc_text = self.editor.toPlainText()
        sel_range = _python_selection(doc_text, cursor)

        tx = self.voice_editor.plan_edit(
            document_text=doc_text,
            selected_range=sel_range,
            instruction=instruction,
            target_id=self._target_id,
            target_type="scratchpad"
        )
        self.active_transaction = tx

        if tx.can_apply:
            self.lbl_edit_diff.setText(f"✓ Planned: {tx.diff_preview}")
            self.lbl_edit_diff.setStyleSheet("color: #34D399; font-size: 12px; font-family: monospace;")
            self.btn_apply_edit.setEnabled(True)
            if auto_apply and tx.operation != "remove_selection":
                self._on_apply_edit()
        else:
            self.lbl_edit_diff.setText(f"⚠ {tx.error_message or tx.diff_preview}")
            self.lbl_edit_diff.setStyleSheet("color: #F87171; font-size: 12px; font-family: monospace;")
            self.btn_apply_edit.setEnabled(False)

        return tx

    def _on_dictate_clicked(self):
        if self.on_dictate_toggle:
            self.on_dictate_toggle()
        self.dictate_requested.emit()

    def set_recording_state(self, is_recording: bool):
        if is_recording:
            self.btn_dictate.setText("⏹ Stop Dictation")
            self.btn_dictate.setStyleSheet("""
                QPushButton {
                    background-color: #DC2626;
                    color: #FFFFFF;
                    font-weight: bold;
                    padding: 7px 16px;
                    border-radius: 6px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #B91C1C;
                }
            """)
        else:
            self.btn_dictate.setText("🎤 Dictate into Pad")
            self.btn_dictate.setStyleSheet("""
                QPushButton {
                    background-color: #0284C7;
                    color: #FFFFFF;
                    font-weight: bold;
                    padding: 7px 16px;
                    border-radius: 6px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #0369A1;
                }
            """)

    def insert_text(self, text: str):
        if not text:
            return
        cursor = self.editor.textCursor()
        if not cursor.atBlockStart() and not self.editor.toPlainText().endswith(" "):
            cursor.insertText(" ")
        cursor.insertText(text)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()

    def _on_text_changed(self):
        self._invalidate_preview()
        text = self.editor.toPlainText()
        words = len(text.split())
        chars = len(text)
        self.lbl_stats.setText(f"{words} words | {chars} chars")
        self._autosave_timer.start(1500)

    def _invalidate_preview(self):
        if self.active_transaction is not None:
            self.voice_editor.cancel_transaction(self.active_transaction.transaction_id)
            self.active_transaction = None
            self.btn_apply_edit.setEnabled(False)
            self.lbl_edit_diff.setText("Text, selection, or instruction changed. Preview again.")

    def _get_stt_engine(self):
        if self._stt_engine is None:
            try:
                from engine.stt_engine import STTEngine
                from engine.config import load_config
                self._stt_engine = STTEngine(load_config())
            except Exception as e:
                logger.warning(f"Could not load STTEngine for voice commands: {e}")
        return self._stt_engine

    def _get_audio_recorder(self):
        if self._audio_recorder is None:
            try:
                from engine.audio_recorder import AudioRecorder
                from engine.config import load_config
                cfg = load_config()
                mic_dev = cfg.get("audio_device_index", cfg.get("mic_device"))
                self._audio_recorder = AudioRecorder(device=mic_dev)
            except Exception as e:
                logger.warning(f"Could not load AudioRecorder for voice commands: {e}")
        return self._audio_recorder

    def _toggle_command_recording(self):
        if self._is_recording_command:
            self._stop_command_recording()
        else:
            self._start_command_recording()

    def _reset_speak_button_style(self):
        self.btn_speak_command.setText("🎙️ Speak Command")
        self.btn_speak_command.setStyleSheet("""
            QPushButton {
                background-color: #7C3AED;
                color: #FFFFFF;
                font-weight: 600;
                padding: 8px 12px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #6D28D9; }
        """)

    def _cancel_command_recording(self):
        """Immediately closes recording stream and restores UI to idle state."""
        if self._is_recording_command:
            self._is_recording_command = False
            self._reset_speak_button_style()
            recorder = self._get_audio_recorder()
            if recorder:
                try:
                    recorder.stop_recording(keep_stream_alive=False)
                except Exception:
                    pass

    def _start_command_recording(self):
        # Invalidate any prior in-flight background worker and cancel pending results
        self._active_request_id += 1
        if self._command_worker and self._command_worker.isRunning():
            try:
                self._command_worker.cancel()
                self._command_worker.quit()
                self._command_worker.wait(100)
            except Exception:
                pass

        recorder = self._get_audio_recorder()
        if not recorder:
            self.lbl_edit_diff.setText("⚠ Microphone is not available.")
            self.lbl_edit_diff.setStyleSheet("color: #EF4444; font-size: 12px; font-family: monospace;")
            return

        self._is_recording_command = True
        self.btn_speak_command.setText("⏹ Stop Listening")
        self.btn_speak_command.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #B91C1C; }
        """)
        self.lbl_edit_diff.setText("🎙️ Listening for voice command... (Speak now, then click Stop)")
        self.lbl_edit_diff.setStyleSheet("color: #C084FC; font-size: 12px; font-family: monospace; padding-left: 4px;")
        recorder.start_recording()

    def _stop_command_recording(self):
        if not self._is_recording_command:
            return
        self._is_recording_command = False
        self._reset_speak_button_style()

        recorder = self._get_audio_recorder()
        audio = None
        if recorder:
            try:
                audio = recorder.stop_recording(keep_stream_alive=False)
            except Exception as e:
                logger.warning(f"Error stopping command recorder: {e}")

        if audio is None or len(audio) == 0:
            self.lbl_edit_diff.setText("⚠ No audio captured. Try speaking again.")
            self.lbl_edit_diff.setStyleSheet("color: #EF4444; font-size: 12px; font-family: monospace;")
            return

        stt = self._get_stt_engine()
        if not stt:
            self.lbl_edit_diff.setText("⚠ STT engine is not available.")
            self.lbl_edit_diff.setStyleSheet("color: #EF4444; font-size: 12px; font-family: monospace;")
            return

        # Execute transcription and edit planning on a background thread to prevent UI freezing
        self.lbl_edit_diff.setText("Transcribing voice command...")
        self.lbl_edit_diff.setStyleSheet("color: #A5B4FC; font-size: 12px; font-family: monospace; padding-left: 4px;")

        self._active_request_id += 1
        req_id = self._active_request_id

        doc_text = self.editor.toPlainText()
        cursor = self.editor.textCursor()
        sel_range = _python_selection(doc_text, cursor)

        self._command_worker = VoiceCommandWorker(
            stt=stt,
            editor=self.voice_editor,
            doc_text=doc_text,
            sel_range=sel_range,
            audio=audio,
            target_id=self._target_id,
            request_id=req_id,
            parent=self
        )
        self._command_worker.status_updated.connect(self._on_command_worker_status)
        self._command_worker.command_planned.connect(self._on_command_worker_result)
        self._command_worker.start()

    def _on_command_worker_status(self, request_id: int, msg: str):
        if request_id != self._active_request_id or self.edit_panel.isHidden():
            return
        self.lbl_edit_diff.setText(msg)
        self.lbl_edit_diff.setStyleSheet("color: #A5B4FC; font-size: 12px; font-family: monospace; padding-left: 4px;")

    def _on_command_worker_result(self, request_id: int, cleaned: str, tx: Optional[EditTransaction], err: str):
        # Ignore cancelled or superseded results; never revive preview or enable apply
        if request_id != self._active_request_id or self.edit_panel.isHidden():
            return

        if err or not tx:
            self.lbl_edit_diff.setText(f"⚠ {err or 'Command planning failed.'}")
            self.lbl_edit_diff.setStyleSheet("color: #EF4444; font-size: 12px; font-family: monospace;")
            return

        self.input_edit_command.blockSignals(True)
        self.input_edit_command.setText(cleaned)
        self.input_edit_command.blockSignals(False)

        self.active_transaction = tx
        if tx.can_apply:
            self.lbl_edit_diff.setText(f"✓ Planned: {tx.diff_preview}")
            self.lbl_edit_diff.setStyleSheet("color: #34D399; font-size: 12px; font-family: monospace;")
            self.btn_apply_edit.setEnabled(True)
        else:
            self.lbl_edit_diff.setText(f"⚠ {tx.error_message or tx.diff_preview}")
            self.lbl_edit_diff.setStyleSheet("color: #F87171; font-size: 12px; font-family: monospace;")
            self.btn_apply_edit.setEnabled(False)

        self.command_planned.emit(tx)

    def process_voice_command_audio(self, audio) -> Optional[EditTransaction]:
        """
        Transcribes recorded audio and plans the voice edit transaction synchronously.
        Used for headless testing and programmatic invocation.
        """
        stt = self._get_stt_engine()
        if not stt:
            self.lbl_edit_diff.setText("⚠ STT engine is not available.")
            self.lbl_edit_diff.setStyleSheet("color: #EF4444; font-size: 12px; font-family: monospace;")
            return None

        try:
            res = stt.transcribe(audio)
            raw_instruction = res.get("text", "").strip() if isinstance(res, dict) else str(res).strip()
        except Exception as e:
            self.lbl_edit_diff.setText(f"⚠ Transcription failed: {e}")
            self.lbl_edit_diff.setStyleSheet("color: #EF4444; font-size: 12px; font-family: monospace;")
            return None

        if not raw_instruction:
            self.lbl_edit_diff.setText("⚠ No clear speech recognized. Please repeat the command.")
            self.lbl_edit_diff.setStyleSheet("color: #EF4444; font-size: 12px; font-family: monospace;")
            return None

        cleaned_instruction = raw_instruction.rstrip(".!? ")
        self.input_edit_command.setText(cleaned_instruction)
        self._on_preview_edit()
        if self.active_transaction:
            self.command_planned.emit(self.active_transaction)
        return self.active_transaction

    def _cancel_edit(self):
        self._active_request_id += 1
        self._cancel_command_recording()
        if self._command_worker:
            try:
                self._command_worker.cancel()
                if self._command_worker.isRunning():
                    self._command_worker.quit()
                    self._command_worker.wait(100)
            except Exception:
                pass
        self._invalidate_preview()
        self.edit_panel.setVisible(False)

    def _copy_all(self):
        text = self.editor.toPlainText().strip()
        if not text:
            return
        try:
            pyperclip.copy(text)
            self.lbl_stats.setText("✓ Copied to clipboard!")
            QTimer.singleShot(1500, self._on_text_changed)
        except Exception as e:
            QMessageBox.warning(self, "Copy Failed", f"Could not copy text: {e}")

    def _bulletize(self):
        text = self.editor.toPlainText().strip()
        if not text:
            return
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        bulleted = "\n".join(f"- {line.lstrip('-* ')}" for line in lines)
        self.editor.setPlainText(bulleted)

    def _clear_pad(self):
        text = self.editor.toPlainText().strip()
        if not text:
            return
        reply = QMessageBox.question(
            self,
            "Clear Scratchpad",
            "Are you sure you want to clear your scratchpad? You can undo this action.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._cleared_backup = self.editor.toPlainText()
            self.editor.clear()
            self._save_autosave()
            self.btn_undo_clear.setVisible(True)

    def _undo_clear(self):
        if getattr(self, "_cleared_backup", None):
            self.editor.setPlainText(self._cleared_backup)
            self._cleared_backup = None
            self.btn_undo_clear.setVisible(False)
            self._save_autosave()

    def save_now(self):
        self._save_autosave()

    def hideEvent(self, event):
        self._active_request_id += 1
        self._cancel_command_recording()
        if self._command_worker:
            try:
                self._command_worker.cancel()
                if self._command_worker.isRunning():
                    self._command_worker.quit()
                    self._command_worker.wait(100)
            except Exception:
                pass
        self._invalidate_preview()
        self.save_now()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._active_request_id += 1
        self._cancel_command_recording()
        if self._command_worker:
            try:
                self._command_worker.cancel()
                if self._command_worker.isRunning():
                    self._command_worker.quit()
                    self._command_worker.wait(100)
            except Exception:
                pass
        self._invalidate_preview()
        self.save_now()
        super().closeEvent(event)

    def _export_file(self):
        text = self.editor.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Export", "Scratchpad is empty.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Scratchpad", str(Path.home() / "scratchpad_notes.md"), "Markdown (*.md);;Text (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                QMessageBox.information(self, "Exported", f"Successfully saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to save file: {e}")

    def _load_autosave(self):
        if AUTOSAVE_FILE.exists():
            try:
                with open(AUTOSAVE_FILE, "r", encoding="utf-8") as f:
                    saved = f.read()
                    if saved.strip():
                        self.editor.setPlainText(saved)
            except Exception:
                pass

    def _save_autosave(self):
        try:
            AUTOSAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(AUTOSAVE_FILE, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
        except Exception:
            pass
