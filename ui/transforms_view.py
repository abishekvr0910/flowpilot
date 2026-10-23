"""
FlowPilot Selected-Text Transforms View (100% Offline & Private)
Wispr Flow Parity & Leapfrog:
- Interactive text transformation interface with instant selected-text extraction
- Presets:
    * Make Concise (✂️)
    * Fix Typos & Grammar (✨)
    * Format as Bullet Points (📋)
    * Professional Tone (💼)
    * Casual Tone (💬)
    * Translate to English (🌐)
- Custom Prompt / Spoken Instruction box with voice input
- FactGuard Invariant safety validation indicator
- Preview and explicit copying; external Replace and Revert are unavailable
"""

import sys
from typing import Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QLineEdit, QFrame, QSplitter, QMessageBox, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
import pyperclip

from engine.transforms_engine import get_transforms_engine, PRESET_TRANSFORMS, TransformsEngine, TransformResult
from engine.text_injector import InjectionStatus


class TransformsView(QWidget):
    transform_applied = Signal(str)

    def __init__(self, parent=None, on_dictate_toggle: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.engine: TransformsEngine = get_transforms_engine()
        self.on_dictate_toggle = on_dictate_toggle
        self._current_result: Optional[TransformResult] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header Bar
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("Selected-Text Transforms")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #F8FAFC;")
        lbl_sub = QLabel("Preview a text transform, then copy the result into your editor.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)

        header.addStretch()

        btn_grab = QPushButton("🔍 Grab Selected Text (Ctrl+Alt+T)")
        btn_grab.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
                padding: 7px 14px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        btn_grab.clicked.connect(self._grab_selection)
        header.addWidget(btn_grab)
        layout.addLayout(header)

        # Preset Quick Grid
        lbl_presets = QLabel("PRESET TRANSFORMS")
        lbl_presets.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748B; margin-top: 4px;")
        layout.addWidget(lbl_presets)

        preset_grid = QGridLayout()
        preset_grid.setSpacing(8)

        presets = list(PRESET_TRANSFORMS.values())
        for i, p in enumerate(presets):
            row = i // 3
            col = i % 3
            btn = QPushButton(f"{p['icon']}  {p['name']}")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #F8FAFC;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-weight: 600;
                    font-size: 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #243247;
                    border: 1px solid #38BDF8;
                    color: #38BDF8;
                }
            """)
            p_id = p["id"]
            btn.clicked.connect(lambda _, tid=p_id: self._execute_preset(tid))
            preset_grid.addWidget(btn, row, col)

        layout.addLayout(preset_grid)

        # Custom Prompt Row
        custom_row = QHBoxLayout()
        custom_row.setSpacing(8)
        self.txt_custom = QLineEdit()
        self.txt_custom.setPlaceholderText("Or type/speak a custom instruction: e.g. 'Make into an email to my team' or 'Summarize in 2 sentences'...")
        self.txt_custom.setStyleSheet("""
            QLineEdit {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #38BDF8;
            }
        """)
        self.txt_custom.returnPressed.connect(self._execute_custom)
        custom_row.addWidget(self.txt_custom, stretch=1)

        btn_run_custom = QPushButton("Apply Prompt")
        btn_run_custom.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-weight: 600;
                padding: 8px 14px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        btn_run_custom.clicked.connect(self._execute_custom)
        custom_row.addWidget(btn_run_custom)
        layout.addLayout(custom_row)

        # Splitter: Original vs Transformed
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #1E293B; width: 2px; }")

        # Left: Original Source
        left_box = QWidget()
        l_layout = QVBoxLayout(left_box)
        l_layout.setContentsMargins(0, 0, 4, 0)
        lbl_orig = QLabel("ORIGINAL SELECTION")
        lbl_orig.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748B;")
        l_layout.addWidget(lbl_orig)

        self.edit_original = QTextEdit()
        self.edit_original.setPlaceholderText("Paste or grab selected text from any app to begin...")
        self.edit_original.setStyleSheet(self._editor_style())
        l_layout.addWidget(self.edit_original)
        splitter.addWidget(left_box)

        # Right: Transformed Output
        right_box = QWidget()
        r_layout = QVBoxLayout(right_box)
        r_layout.setContentsMargins(4, 0, 0, 0)

        r_hdr = QHBoxLayout()
        lbl_trans = QLabel("TRANSFORMED OUTPUT")
        lbl_trans.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748B;")
        r_hdr.addWidget(lbl_trans)
        r_hdr.addStretch()

        self.lbl_factguard = QLabel("🛡️ FactGuard: Verified")
        self.lbl_factguard.setStyleSheet("font-size: 11px; color: #10B981; font-weight: bold;")
        r_hdr.addWidget(self.lbl_factguard)
        r_layout.addLayout(r_hdr)

        self.edit_transformed = QTextEdit()
        self.edit_transformed.setPlaceholderText("Transformed text will appear here with FactGuard entity preservation...")
        self.edit_transformed.setStyleSheet(self._editor_style())
        r_layout.addWidget(self.edit_transformed)
        splitter.addWidget(right_box)

        layout.addWidget(splitter, stretch=1)

        # Footer Action Bar
        footer = QHBoxLayout()
        footer.setSpacing(10)

        self.btn_copy = QPushButton("📋 Copy Output")
        self.btn_copy.setStyleSheet(self._btn_secondary_style())
        self.btn_copy.setToolTip("Copies the preview to your clipboard when you click.")
        self.btn_copy.clicked.connect(self._copy_output)
        footer.addWidget(self.btn_copy)

        self.btn_revert = QPushButton("↩ Revert Last Replace")
        self.btn_revert.setStyleSheet(self._btn_secondary_style())
        self.btn_revert.setToolTip("External revert is unavailable because the prior edit cannot be verified. Use your editor's Undo.")
        self.btn_revert.setEnabled(False)
        self.btn_revert.clicked.connect(self._revert_last)
        footer.addWidget(self.btn_revert)

        footer.addStretch()

        self.btn_replace = QPushButton("⚡ Replace in Target Window")
        self.btn_replace.setToolTip("In-place replacement requires a verified document transaction adapter. For external applications, use 'Copy Output'.")
        self.btn_replace.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: bold;
                padding: 9px 18px;
                border-radius: 6px;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_replace.clicked.connect(self._replace_in_target)
        footer.addWidget(self.btn_replace)

        layout.addLayout(footer)

        self.lbl_external_edit = QLabel(
            "External Replace and Revert are unavailable while document changes "
            "cannot be verified. Use Copy Output, then paste in your editor."
        )
        self.lbl_external_edit.setWordWrap(True)
        layout.addWidget(self.lbl_external_edit)

        # Enforce initial safe UI state
        self.btn_replace.setEnabled(False)
        self.lbl_factguard.setText("")

        # Invalidate stale results when input text or custom prompt changes
        self.edit_original.textChanged.connect(self._on_input_changed)
        self.txt_custom.textChanged.connect(self._on_input_changed)

    def _on_input_changed(self):
        self._current_result = None
        self.btn_replace.setEnabled(False)
        self.lbl_factguard.setText("")
        self.edit_transformed.setStyleSheet(self._editor_style())

    def _editor_style(self) -> str:
        return """
            QTextEdit {
                background-color: #0B0F19;
                color: #F8FAFC;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-size: 13px;
                line-height: 1.6;
            }
            QTextEdit:focus {
                border: 1px solid #38BDF8;
            }
        """

    def _btn_secondary_style(self) -> str:
        return """
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                font-weight: 600;
                padding: 8px 14px;
                border-radius: 6px;
                border: 1px solid #334155;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #38BDF8;
            }
        """

    def _grab_selection(self):
        text = self.engine.get_selected_text_from_active_window()
        if text:
            self.edit_original.setPlainText(text)
        else:
            QMessageBox.information(
                self, "Grab Selection",
                "No text was currently highlighted in the foreground application.\n"
                "Please select text in Notepad, Word, browser, or code editor and try again."
            )

    def _execute_preset(self, preset_id: str):
        text = self.edit_original.toPlainText().strip()
        if not text:
            self._grab_selection()
            text = self.edit_original.toPlainText().strip()
        if not text:
            return

        res = self.engine.transform_text(text, preset_id)
        self._current_result = res
        self.edit_transformed.setPlainText(res.candidate_text)
        self._update_status_ui(res)

    def _execute_custom(self):
        text = self.edit_original.toPlainText().strip()
        prompt = self.txt_custom.text().strip()
        if not text:
            self._grab_selection()
            text = self.edit_original.toPlainText().strip()
        if not text or not prompt:
            return

        res = self.engine.transform_text(text, "custom", custom_instruction=prompt)
        self._current_result = res
        self.edit_transformed.setPlainText(res.candidate_text)
        self._update_status_ui(res)

    def _update_status_ui(self, res: TransformResult):
        self.btn_replace.setEnabled(False)
        self.edit_transformed.setStyleSheet(self._editor_style())

        if res.status == "success":
            self.lbl_factguard.setText("🛡️ FactGuard: Verified (Invariants Preserved)")
            self.lbl_factguard.setStyleSheet("font-size: 11px; color: #10B981; font-weight: bold;")
        elif res.status == "unsupported":
            msg = res.error_message or "This instruction needs the optional local writing model. Your text was not changed."
            self.lbl_factguard.setText(f"ℹ️ Unsupported: {msg}")
            self.lbl_factguard.setStyleSheet("font-size: 11px; color: #94A3B8; font-weight: bold;")
        elif res.status == "unavailable":
            msg = res.error_message or "Required model is unavailable. Your text was not changed."
            self.lbl_factguard.setText(f"⚠️ Unavailable: {msg}")
            self.lbl_factguard.setStyleSheet("font-size: 11px; color: #F59E0B; font-weight: bold;")
        elif res.status == "blocked":
            self.lbl_factguard.setText("⛔ Blocked: FactGuard Invariant Violation")
            self.lbl_factguard.setStyleSheet("font-size: 11px; color: #EF4444; font-weight: bold;")
        else:
            self.lbl_factguard.setText("")

    def _replace_in_target(self):
        if not self._current_result or not self._current_result.can_apply:
            QMessageBox.warning(self, "Replace Blocked", "This text cannot be applied because the transformation was not successful or was blocked by FactGuard.")
            return

        transformed = self.edit_transformed.toPlainText()
        if not transformed:
            return

        inj_res = self.engine.replace_selection(transformed, result=self._current_result)
        if inj_res.status == InjectionStatus.CONFIRMED_INSERTED:
            self.transform_applied.emit(transformed)
            self.edit_transformed.setStyleSheet("""
                QTextEdit {
                    background-color: #052E16;
                    color: #86EFAC;
                    border: 1px solid #10B981;
                    border-radius: 8px;
                    padding: 12px;
                    font-family: 'Consolas', monospace;
                    font-size: 13px;
                }
            """)
            QMessageBox.information(self, "Replace Confirmed", "Transformed text was verified and inserted into the target document.")
        elif inj_res.status == InjectionStatus.SENT_UNVERIFIED:
            QMessageBox.information(self, "Sent for Verification", "Sent, please check target window. Insertion could not be verified automatically.")
        elif inj_res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE:
            msg = inj_res.error_message or "External in-place replacement unavailable. Use 'Copy Output' to paste manually."
            QMessageBox.warning(self, "Replace Unavailable", f"{msg}\n\nTransformed text is preserved in memory. Click 'Copy Output' to copy.")
        else:
            QMessageBox.warning(self, "Replace Refused", inj_res.error_message or "Could not inject transformed text into target window.")

    def _revert_last(self):
        inj_res = self.engine.revert_last_transform()
        if inj_res.status == InjectionStatus.CONFIRMED_INSERTED:
            QMessageBox.information(self, "Reverted", "Restored original untransformed text back into the application.")
        elif inj_res.status == InjectionStatus.SENT_UNVERIFIED:
            QMessageBox.information(self, "Revert Sent", "Sent, please check target window. Document restoration could not be verified automatically.")
        elif inj_res.status == InjectionStatus.CANCELLED:
            QMessageBox.warning(self, "Revert Refused", inj_res.error_message or "No previous transform found to revert.")
        else:
            QMessageBox.warning(self, "Revert Unavailable", inj_res.error_message or "Cannot revert in external window without verified document revision.")

    def _copy_output(self):
        text = self.edit_transformed.toPlainText().strip()
        if text:
            pyperclip.copy(text)
            self.btn_copy.setText("✓ Copied to Clipboard!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 Copy Output"))
