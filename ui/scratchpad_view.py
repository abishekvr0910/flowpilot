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

from pathlib import Path
from typing import Optional, Callable, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QTextCursor, QColor
import pyperclip

from engine.voice_editor import get_voice_editor, VoiceEditor, EditTransaction

AUTOSAVE_FILE = Path.home() / ".flowpilot" / "scratchpad_autosave.txt"


class ScratchpadView(QWidget):
    dictate_requested = Signal()

    def __init__(self, parent=None, on_dictate_toggle: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_dictate_toggle = on_dictate_toggle
        self.voice_editor: VoiceEditor = get_voice_editor()
        self.active_transaction: Optional[EditTransaction] = None
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
        self.btn_cancel_edit.clicked.connect(lambda: self.edit_panel.setVisible(False))

        panel_row1.addWidget(self.input_edit_command, 5)
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
        sel_range = (cursor.selectionStart(), cursor.selectionEnd())
        doc_text = self.editor.toPlainText()

        tx = self.voice_editor.plan_edit(
            document_text=doc_text,
            selected_range=sel_range,
            instruction=instruction,
            target_id="scratchpad:editor",
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
        sel_range = (cursor.selectionStart(), cursor.selectionEnd())
        doc_text = self.editor.toPlainText()

        ok, resulting_text, msg = self.voice_editor.apply_transaction(
            transaction=self.active_transaction,
            current_document_text=doc_text,
            current_selection=sel_range
        )

        if ok:
            # Preserve cursor near the edited position
            new_cursor_pos = min(len(resulting_text), self.active_transaction.selected_range[1])
            self.editor.setPlainText(resulting_text)
            new_cursor = self.editor.textCursor()
            new_cursor.setPosition(new_cursor_pos)
            self.editor.setTextCursor(new_cursor)

            self.lbl_edit_diff.setText(f"✓ Applied! (Say 'undo that edit' to revert)")
            self.lbl_edit_diff.setStyleSheet("color: #38BDF8; font-size: 12px; font-family: monospace;")
            self.btn_apply_edit.setEnabled(False)
            self.active_transaction = None
            self._save_autosave()
            QTimer.singleShot(2500, lambda: self.edit_panel.setVisible(False))
        else:
            self.lbl_edit_diff.setText(f"✕ Apply failed: {msg}")
            self.lbl_edit_diff.setStyleSheet("color: #EF4444; font-size: 12px; font-family: monospace;")

    def execute_voice_command(self, instruction: str, auto_apply: bool = False) -> EditTransaction:
        """
        Executes or plans a voice editing command directly inside the Scratchpad canvas.
        If auto_apply is True and command is unambiguous, applies immediately.
        """
        self.edit_panel.setVisible(True)
        self.input_edit_command.setText(instruction)

        cursor = self.editor.textCursor()
        sel_range = (cursor.selectionStart(), cursor.selectionEnd())
        doc_text = self.editor.toPlainText()

        tx = self.voice_editor.plan_edit(
            document_text=doc_text,
            selected_range=sel_range,
            instruction=instruction,
            target_id="scratchpad:editor",
            target_type="scratchpad"
        )
        self.active_transaction = tx

        if tx.can_apply:
            self.lbl_edit_diff.setText(f"✓ Planned: {tx.diff_preview}")
            self.lbl_edit_diff.setStyleSheet("color: #34D399; font-size: 12px; font-family: monospace;")
            self.btn_apply_edit.setEnabled(True)
            if auto_apply:
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
        text = self.editor.toPlainText()
        words = len(text.split())
        chars = len(text)
        self.lbl_stats.setText(f"{words} words | {chars} chars")
        self._autosave_timer.start(1500)

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
        self.save_now()
        super().hideEvent(event)

    def closeEvent(self, event):
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
