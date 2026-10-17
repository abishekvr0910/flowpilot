"""
FlowPilot In-App Voice Scratchpad Canvas
A native drafting workspace with:
- Live voice dictation directly into the editor cursor
- Word and character count telemetry
- One-click markdown formatting, copy-all, and export
- Persistent local auto-save
"""

from pathlib import Path
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QFileDialog, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QTextCursor
import pyperclip

AUTOSAVE_FILE = Path.home() / ".flowpilot" / "scratchpad_autosave.txt"

class ScratchpadView(QWidget):
    dictate_requested = Signal()

    def __init__(self, parent=None, on_dictate_toggle: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_dictate_toggle = on_dictate_toggle
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
        lbl_subtitle = QLabel("Draft notes, transform ideas, or dictate continuously without switching apps.")
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

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Text Drafting Canvas
        self.editor = QTextEdit(self)
        self.editor.setPlaceholderText("Start typing or press 'Dictate into Pad' (or your global hotkey Ctrl+Shift+Space) to speak your thoughts...")
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
        if not self.editor.toPlainText().strip():
            return
        reply = QMessageBox.question(
            self,
            "Clear Scratchpad",
            "Are you sure you want to clear your scratchpad? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.editor.clear()
            self._save_autosave()

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
