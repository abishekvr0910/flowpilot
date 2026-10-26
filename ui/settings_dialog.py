"""
Feature 28: FlowPilot Settings & Personalization Dialog
Allows configuring:
1. General Settings: STT model size, Writing Tone mode, Global Hotkeys, Audio Ducking, and Audio Cues.
2. Multilingual: Primary language selection from LanguageRegistry with native scripts and auto-detect.
3. Personalization: Custom Dictionary (technical glossary, domain terms, phonetic aliases) and Voice Snippets.
4. Dictation History: Live searchable log with copy and clear actions.
"""

from typing import Dict, Any, Callable, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QComboBox, QCheckBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QLineEdit,
    QTextEdit, QFileDialog, QSplitter, QRadioButton, QButtonGroup, QScrollArea,
    QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import pyperclip
import json
import logging

logger = logging.getLogger("FlowPilot.SettingsDialog")

from engine.language_registry import LanguageRegistry
from engine.personalization import PersonalizationEngine
from engine.hotkey_service import Win32HotkeyService
from ui.workspace_style import workspace_style, label, harmonize_legacy_styles, guard_wheel_events

class SettingsDialog(QDialog):
    def __init__(
        self,
        config: Dict[str, Any],
        on_save: Callable[[Dict[str, Any]], None],
        personalization: Optional[PersonalizationEngine] = None,
        parent=None,
        embedded: bool = False,
    ):
        super().__init__(parent)
        self.embedded = embedded
        if embedded:
            self.setWindowFlags(Qt.Widget)
        self.config = dict(config)
        self.on_save = on_save
        self.personalization = personalization or PersonalizationEngine()
        self.setWindowTitle("FlowPilot - Settings & Personalization")
        self.resize(900, 720)
        self.setMinimumSize(640, 480)
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("WorkspacePage")
        theme = self.config.get("ui_theme", "sand")
        self.setStyleSheet(workspace_style(theme))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 22)
        layout.setSpacing(16)
        layout.addWidget(label("Settings", "title"))
        layout.addWidget(label("Your microphone, language and shortcuts. Tuned to the way you work."))

        self.tabs = QTabWidget(self)
        self.tabs.setMinimumWidth(0)
        self.tabs.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        general_scroll = QScrollArea()
        general_scroll.setWidgetResizable(True)
        general_scroll.setMinimumWidth(0)
        general_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        general_scroll.setWidget(self._build_general_tab())
        self.tabs.addTab(general_scroll, "Dictation")
        self.tabs.addTab(self._build_personalization_tab(), "Words and snippets")
        self.tabs.addTab(self._build_history_tab(), "Legacy history")
        layout.addWidget(self.tabs, 1)

        footer = QVBoxLayout()
        footer.setSpacing(8)
        self.save_status = label("Dictation changes take effect when you save.")
        self.save_status.setWordWrap(True)
        self.save_status.setMinimumWidth(0)
        self.save_status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        footer.addWidget(self.save_status)
        actions = QHBoxLayout()
        actions.addStretch()
        btn_close = QPushButton("Cancel" if self.embedded else "Close", self)
        btn_close.clicked.connect(self.reject)
        actions.addWidget(btn_close)
        btn_save = QPushButton("Save changes", self)
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._save_settings)
        actions.addWidget(btn_save)
        footer.addLayout(actions)
        layout.addLayout(footer)
        harmonize_legacy_styles(self, theme, include_root=False)
        guard_wheel_events(self)

    def reject(self):
        if self.embedded:
            self.rejected.emit()
        else:
            super().reject()

    def _build_general_tab(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("WorkspacePage")
        vbox = QVBoxLayout(widget)
        vbox.setContentsMargins(20, 20, 20, 20)
        vbox.setSpacing(14)
        vbox.addWidget(label("Workspace appearance", "section"))
        self.combo_ui_theme = QComboBox()
        self.combo_ui_theme.addItem("Sand & Stone · warm light", "sand")
        self.combo_ui_theme.addItem("Obsidian · quiet dark", "obsidian")
        current_theme = self.config.get("ui_theme", "sand")
        self.combo_ui_theme.setCurrentIndex(max(0, self.combo_ui_theme.findData(current_theme)))
        vbox.addWidget(self.combo_ui_theme)
        vbox.addWidget(label("The interface changes when you save. Your speech stays on this device."))
        vbox.addWidget(label("Speech & language", "section"))

        # STT Model
        lbl_model = QLabel("Speech model")
        vbox.addWidget(lbl_model)
        self.combo_model = QComboBox()
        self.combo_model.addItems([
            "tiny — smallest model",
            "base — bundled model",
            "small — larger model, more CPU and memory",
            "medium — largest option, more CPU and memory"
        ])
        current_model = self.config.get("local_model_size", "base")
        for i in range(self.combo_model.count()):
            if current_model in self.combo_model.itemText(i):
                self.combo_model.setCurrentIndex(i)
                break
        vbox.addWidget(self.combo_model)
        self._model_chosen_by_user = False
        self.combo_model.activated.connect(lambda _: setattr(self, "_model_chosen_by_user", True))
        vbox.addWidget(label("Larger models require local weights. Speed and accuracy depend on your language and hardware."))

        # Input Audio Microphone
        lbl_mic = QLabel("Microphone")
        vbox.addWidget(lbl_mic)
        self.combo_mic = QComboBox()
        from ui.audio_input_picker import populate_audio_inputs
        populate_audio_inputs(self.combo_mic, self.config)
        vbox.addWidget(self.combo_mic)

        # Primary Language Selector (from LanguageRegistry)
        lbl_lang = QLabel("Dictation language")
        vbox.addWidget(lbl_lang)
        self.combo_lang = QComboBox()
        languages = LanguageRegistry.list_supported_languages()
        cur_lang = self.config.get("language", "auto")
        selected_lang_idx = 0
        for idx, lang in enumerate(languages):
            status_suffix = " (Experimental)" if lang.get("quality_status") == "experimental" else ""
            display_str = f"{lang['name']} ({lang['native_name']}) [{lang['code']}]{status_suffix}"
            self.combo_lang.addItem(display_str, lang["code"])
            if lang["code"] == cur_lang:
                selected_lang_idx = idx
        self.combo_lang.setCurrentIndex(selected_lang_idx)
        vbox.addWidget(self.combo_lang)
        self.lbl_model_guidance = QLabel()
        self.lbl_model_guidance.setWordWrap(True)
        vbox.addWidget(self.lbl_model_guidance)

        self.btn_download_small = QPushButton("Download Multilingual Model (461 MB)")
        self.btn_download_small.setStyleSheet(
            "background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px; border-radius: 6px; margin-top: 6px;"
        )
        self.btn_download_small.setVisible(False)
        self.btn_download_small.clicked.connect(self._start_model_download)
        vbox.addWidget(self.btn_download_small)

        self.progress_download_small = QProgressBar()
        self.progress_download_small.setRange(0, 100)
        self.progress_download_small.setValue(0)
        self.progress_download_small.setStyleSheet(
            "QProgressBar { background-color: #1E293B; border: 1px solid #334155; border-radius: 4px; height: 14px; text-align: center; color: white; font-size: 10px; }"
            "QProgressBar::chunk { background-color: #10B981; border-radius: 3px; }"
        )
        self.progress_download_small.setVisible(False)
        vbox.addWidget(self.progress_download_small)

        self.lbl_download_status = QLabel()
        self.lbl_download_status.setStyleSheet("font-size: 11px; color: #94A3B8; margin-top: 2px;")
        self.lbl_download_status.setVisible(False)
        vbox.addWidget(self.lbl_download_status)

        self.combo_lang.currentIndexChanged.connect(self._on_language_model_guidance)
        self._on_language_model_guidance()

        # Tone / Format Style
        lbl_tone = QLabel("Writing & Transformation Mode:")
        vbox.addWidget(lbl_tone)
        self.combo_tone = QComboBox()
        self.tone_options = [
            ("developer", "Polished: Developer & Code Identifiers (camelCase, snake_case)"),
            ("professional", "Polished: Professional & Formal Grammar"),
            ("casual", "Polished: Natural & Casual Speech (Uncensored)"),
            ("email", "Polished: Email Structure with Greetings & Sign-offs"),
            ("concise", "Polished: Concise & Direct Phrasing"),
            ("verbatim", "Verbatim: 100% Unmodified Faithful Speech")
        ]
        for key, title in self.tone_options:
            self.combo_tone.addItem(title, key)
        cur_mode = self.config.get("active_tone_mode", "developer")
        for i, (key, _) in enumerate(self.tone_options):
            if key == cur_mode:
                self.combo_tone.setCurrentIndex(i)
                break
        vbox.addWidget(self.combo_tone)

        # Dictation Mode (Toggle vs Push-to-Talk)
        vbox.addSpacing(12)
        vbox.addWidget(label("Shortcut & recording", "section"))
        lbl_mode = QLabel("How you start and stop")
        vbox.addWidget(lbl_mode)
        
        mode_layout = QVBoxLayout()
        self.btn_group_mode = QButtonGroup(self)
        self.radio_toggle = QRadioButton("Toggle Mode (Press to start, press again to stop)")
        self.radio_ptt = QRadioButton("Push-to-Talk (Hold to speak, release to stop)")
        self.btn_group_mode.addButton(self.radio_toggle)
        self.btn_group_mode.addButton(self.radio_ptt)
        
        cur_mode = self.config.get("hotkey_mode", "toggle")
        if cur_mode == "push_to_talk":
            self.radio_ptt.setChecked(True)
        else:
            self.radio_toggle.setChecked(True)
            
        mode_layout.addWidget(self.radio_toggle)
        mode_layout.addWidget(self.radio_ptt)
        vbox.addLayout(mode_layout)

        # Primary Shortcut Selector & Availability Check
        lbl_shortcut = QLabel("Primary Global Keyboard Shortcut:")
        vbox.addWidget(lbl_shortcut)

        hk_row = QHBoxLayout()
        self.combo_shortcut = QComboBox()
        self.combo_shortcut.setEditable(True)
        self.combo_shortcut.addItems([
            "F9",
            "Ctrl+Shift+Space",
            "F8",
            "Ctrl+Alt+Space",
            "Win+Alt+Space",
            "Ctrl+F9",
            "Ctrl+Alt+D"
        ])
        cur_hk = self.config.get("hotkey", "Ctrl+Shift+Space").replace("<", "").replace(">", "").strip()
        self.combo_shortcut.setCurrentText(cur_hk)
        hk_row.addWidget(self.combo_shortcut, 3)

        self.btn_test_hk = QPushButton("Test Availability")
        self.btn_test_hk.setStyleSheet("background-color: #0369A1;")
        self.btn_test_hk.clicked.connect(self._test_current_hotkey)
        hk_row.addWidget(self.btn_test_hk, 1)
        vbox.addLayout(hk_row)

        self.lbl_hotkey_status = QLabel("")
        vbox.addWidget(self.lbl_hotkey_status)

        # Audio Ducking Checkbox
        self.chk_ducking = QCheckBox("Silence background music / video while dictating")
        self.chk_ducking.setChecked(self.config.get("ducking_enabled", True))
        vbox.addWidget(self.chk_ducking)

        # Audio Feedback Chimes Checkbox
        self.chk_sound = QCheckBox("Play audible chimes when dictation starts, stops, or cancels")
        self.chk_sound.setChecked(self.config.get("sound_effects_enabled", True))
        vbox.addWidget(self.chk_sound)

        # Hotkey safety banner
        lbl_hotkeys = QLabel(
            "Choose one dictation shortcut, such as F9, and select Toggle or Hold mode above. "
            "Only your chosen key will start dictation. FlowPilot reserves Ctrl+Alt+T for transforms, "
            "Alt+Shift+Z for Paste Last, and Alt+Shift+X for Copy Last. "
            "Test Availability checks whether Windows or another app already owns a shortcut."
        )
        lbl_hotkeys.setStyleSheet("color: #94A3B8; background: #0F172A; padding: 10px; border-radius: 6px; font-size: 11px; line-height: 1.4;")
        lbl_hotkeys.setWordWrap(True)
        vbox.addWidget(lbl_hotkeys)

        vbox.addStretch()
        return widget

    def _build_personalization_tab(self) -> QWidget:
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(12)
        vbox.addWidget(label("Dictionary and snippet edits are saved immediately. Use their dedicated workspace pages for advanced options."))

        # --- SECTION 1: PERSONAL DICTIONARY ---
        lbl_dict = QLabel("Custom Vocabulary & Phonetic Aliases (Biases Whisper & Enforces Casing):")
        lbl_dict.setStyleSheet("font-weight: bold; color: #38BDF8;")
        vbox.addWidget(lbl_dict)

        self.table_dict = QTableWidget()
        self.table_dict.setColumnCount(2)
        self.table_dict.setHorizontalHeaderLabels(["Target Term (Canonical)", "Phonetic Alias / Trigger"])
        self.table_dict.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_dict.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_dict.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_dict.setFixedHeight(120)
        vbox.addWidget(self.table_dict)

        dict_row = QHBoxLayout()
        self.edit_term = QLineEdit()
        self.edit_term.setPlaceholderText("Canonical term (e.g., FlowPilot)")
        dict_row.addWidget(self.edit_term)

        self.edit_alias = QLineEdit()
        self.edit_alias.setPlaceholderText("Spoken alias (e.g., flow pilot)")
        dict_row.addWidget(self.edit_alias)

        btn_add_term = QPushButton("Add / Update Term")
        btn_add_term.clicked.connect(self._add_dict_term)
        dict_row.addWidget(btn_add_term)

        btn_del_term = QPushButton("Delete")
        btn_del_term.setStyleSheet("background-color: #991B1B;")
        btn_del_term.clicked.connect(self._delete_dict_term)
        dict_row.addWidget(btn_del_term)

        vbox.addLayout(dict_row)

        # --- SECTION 2: VOICE SNIPPETS ---
        lbl_snip = QLabel("Voice Snippets (Spoken Triggers Expanded Automatically):")
        lbl_snip.setStyleSheet("font-weight: bold; color: #38BDF8; margin-top: 8px;")
        vbox.addWidget(lbl_snip)

        self.table_snip = QTableWidget()
        self.table_snip.setColumnCount(2)
        self.table_snip.setHorizontalHeaderLabels(["Spoken Trigger Phrase", "Expanded Template / Text"])
        self.table_snip.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_snip.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_snip.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_snip.setFixedHeight(120)
        vbox.addWidget(self.table_snip)

        snip_row = QHBoxLayout()
        self.edit_trigger = QLineEdit()
        self.edit_trigger.setPlaceholderText("Spoken trigger (e.g., insert my calendly)")
        snip_row.addWidget(self.edit_trigger)

        self.edit_expansion = QLineEdit()
        self.edit_expansion.setPlaceholderText("Expansion (e.g., https://calendly.com/me)")
        snip_row.addWidget(self.edit_expansion)

        btn_add_snip = QPushButton("Add Snippet")
        btn_add_snip.clicked.connect(self._add_snippet)
        snip_row.addWidget(btn_add_snip)

        btn_del_snip = QPushButton("Delete")
        btn_del_snip.setStyleSheet("background-color: #991B1B;")
        btn_del_snip.clicked.connect(self._delete_snippet)
        snip_row.addWidget(btn_del_snip)

        vbox.addLayout(snip_row)

        # --- IMPORT / EXPORT ROW ---
        io_row = QHBoxLayout()
        io_row.addStretch()

        btn_export = QPushButton("Export JSON (Share with Team)")
        btn_export.setStyleSheet("background-color: #047857;")
        btn_export.clicked.connect(self._export_personalization)
        io_row.addWidget(btn_export)

        btn_import = QPushButton("Import JSON")
        btn_import.setStyleSheet("background-color: #0D9488;")
        btn_import.clicked.connect(self._import_personalization)
        io_row.addWidget(btn_import)

        vbox.addLayout(io_row)

        self._populate_personalization()
        return widget

    def _build_history_tab(self) -> QWidget:
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.addWidget(label("Older profile history only. For the current dictation vault, use History & audio in the workspace."))

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Time", "Target App", "Duration", "Transcribed Text"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        vbox.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_copy = QPushButton("Copy Selected Text")
        btn_copy.clicked.connect(self._copy_selected_history)
        btn_row.addWidget(btn_copy)

        btn_clear = QPushButton("Clear History")
        btn_clear.setStyleSheet("background-color: #991B1B;")
        btn_clear.clicked.connect(self._clear_history)
        btn_row.addWidget(btn_clear)

        vbox.addLayout(btn_row)
        self._populate_history()
        return widget

    # --- PERSONALIZATION HELPERS ---

    def _populate_personalization(self):
        # Dictionary
        dict_items = self.personalization.dictionary
        self.table_dict.setRowCount(len(dict_items))
        for r, item in enumerate(dict_items):
            self.table_dict.setItem(r, 0, QTableWidgetItem(item.get("term", "")))
            aliases = item.get("aliases") or ([item["alias"]] if item.get("alias") else [])
            self.table_dict.setItem(r, 1, QTableWidgetItem(", ".join(aliases)))

        # Snippets
        snippets = self.personalization.snippets
        self.table_snip.setRowCount(len(snippets))
        for r, item in enumerate(snippets):
            self.table_snip.setItem(r, 0, QTableWidgetItem(item.get("trigger", "")))
            self.table_snip.setItem(r, 1, QTableWidgetItem(item.get("expansion", "")))

    def _add_dict_term(self):
        term = self.edit_term.text().strip()
        alias = self.edit_alias.text().strip()
        if not term:
            QMessageBox.warning(self, "Invalid Term", "Please provide a valid term.")
            return
        aliases = [a.strip() for a in alias.split(",") if a.strip()] if alias else []
        self.personalization.add_term(term, alias=aliases[0] if aliases else "", aliases=aliases)
        self.edit_term.clear()
        self.edit_alias.clear()
        self._populate_personalization()

    def _delete_dict_term(self):
        sel = self.table_dict.selectedItems()
        if sel:
            row = sel[0].row()
            term_item = self.table_dict.item(row, 0)
            if term_item:
                self.personalization.remove_term(term_item.text())
                self._populate_personalization()

    def _add_snippet(self):
        trigger = self.edit_trigger.text().strip()
        expansion = self.edit_expansion.text().strip()
        if not trigger or not expansion:
            QMessageBox.warning(self, "Invalid Snippet", "Please provide both trigger and expansion.")
            return
        self.personalization.add_snippet(trigger, expansion)
        self.edit_trigger.clear()
        self.edit_expansion.clear()
        self._populate_personalization()

    def _delete_snippet(self):
        sel = self.table_snip.selectedItems()
        if sel:
            row = sel[0].row()
            trig_item = self.table_snip.item(row, 0)
            if trig_item:
                self.personalization.remove_snippet(trig_item.text())
                self._populate_personalization()

    def _export_personalization(self):
        json_data = self.personalization.export_json()
        path, _ = QFileDialog.getSaveFileName(self, "Export Dictionary & Snippets", "flowpilot_personalization.json", "JSON Files (*.json)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(json_data)
                QMessageBox.information(self, "Export Successful", f"Saved configuration to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save file: {e}")

    def _import_personalization(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Dictionary & Snippets", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                success = self.personalization.import_json(content, merge=True)
                if success:
                    self._populate_personalization()
                    QMessageBox.information(self, "Import Successful", "Dictionary and snippets imported successfully!")
                else:
                    QMessageBox.critical(self, "Import Error", "Failed to parse JSON file.")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Error reading file: {e}")

    # --- HISTORY HELPERS ---

    def _populate_history(self):
        history = self.config.get("history", [])
        self.table.setRowCount(len(history))
        for row, entry in enumerate(history):
            self.table.setItem(row, 0, QTableWidgetItem(entry.get("timestamp", "")))
            self.table.setItem(row, 1, QTableWidgetItem(entry.get("target_app", "")))
            self.table.setItem(row, 2, QTableWidgetItem(f"{entry.get('duration_sec', 0)}s"))
            self.table.setItem(row, 3, QTableWidgetItem(entry.get("formatted_text", entry.get("raw_text", ""))))

    def _copy_selected_history(self):
        sel = self.table.selectedItems()
        if sel:
            row = sel[0].row()
            text_item = self.table.item(row, 3)
            if text_item:
                pyperclip.copy(text_item.text())
                QMessageBox.information(self, "Copied", "Dictation text copied to clipboard!")

    def _clear_history(self):
        self.config["history"] = []
        self._populate_history()
        self.on_save(self.config)

    def _test_current_hotkey(self):
        hk = self.combo_shortcut.currentText().strip()
        if not hk:
            self.lbl_hotkey_status.setStyleSheet("color: #EF4444; font-size: 12px;")
            self.lbl_hotkey_status.setText("Please enter or select a hotkey to test.")
            return False
        cur_hk = self.config.get("hotkey", "")
        avail, msg = Win32HotkeyService.test_hotkey_availability(hk, currently_active_hotkey=cur_hk)
        if avail:
            self.lbl_hotkey_status.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px;")
            self.lbl_hotkey_status.setText(f"[AVAILABLE] {msg}")
        else:
            self.lbl_hotkey_status.setStyleSheet("color: #EF4444; font-weight: bold; font-size: 12px;")
            self.lbl_hotkey_status.setText(f"[CONFLICT/INVALID] {msg}")
        return avail

    def _on_language_model_guidance(self, *_args):
        """Make the bundled Indic model recommendation visible and one step away."""
        language = self.combo_lang.currentData()
        if language not in ("hi", "ta", "ml"):
            self.lbl_model_guidance.setText("")
            if hasattr(self, "btn_download_small"):
                self.btn_download_small.setVisible(False)
            if hasattr(self, "progress_download_small"):
                self.progress_download_small.setVisible(False)
            if hasattr(self, "lbl_download_status"):
                self.lbl_download_status.setVisible(False)
            return
        if (language != self.config.get("language") and not self._model_chosen_by_user
                and self.combo_model.currentText().startswith("base")):
            for index in range(self.combo_model.count()):
                if self.combo_model.itemText(index).startswith("small"):
                    self.combo_model.setCurrentIndex(index)
                    break
        selected_small = self.combo_model.currentText().startswith("small")
        import os
        from engine.stt_engine import STTEngine
        small_path = STTEngine.resolve_model_path("small")
        has_small = bool(small_path and os.path.isfile(os.path.join(small_path, "model.bin")))
        if selected_small:
            if has_small:
                self.lbl_model_guidance.setText(
                    "✓ Local small model file found. The small model is selected for this language. Recognition still needs a real voice check."
                )
                self.lbl_model_guidance.setStyleSheet("font-size: 11px; color: #10B981;")
                if hasattr(self, "btn_download_small"):
                    self.btn_download_small.setVisible(False)
                if hasattr(self, "progress_download_small"):
                    self.progress_download_small.setVisible(False)
                if hasattr(self, "lbl_download_status"):
                    self.lbl_download_status.setVisible(False)
            else:
                self.lbl_model_guidance.setText(
                    "Local small model file was not found. Download or install the model before relying on this language. Recognition still needs a real voice check."
                )
                self.lbl_model_guidance.setStyleSheet("font-size: 11px; color: #F59E0B;")
                if hasattr(self, "btn_download_small"):
                    self.btn_download_small.setVisible(True)
        else:
            self.lbl_model_guidance.setText(
                "The bundled small model is recommended for Hindi, Tamil, and Malayalam. "
                "Select small above; real voice accuracy is still being evaluated."
            )
            self.lbl_model_guidance.setStyleSheet("font-size: 11px; color: #F59E0B;")
            if hasattr(self, "btn_download_small"):
                self.btn_download_small.setVisible(not has_small)

    def _start_model_download(self):
        try:
            from engine.model_downloader import ModelDownloadWorker
        except ImportError:
            ModelDownloadWorker = None

        if not ModelDownloadWorker:
            QMessageBox.warning(self, "Download Unavailable", "Background download worker is unavailable.")
            return

        self.btn_download_small.setEnabled(False)
        self.btn_download_small.setText("Downloading model...")
        self.progress_download_small.setVisible(True)
        self.progress_download_small.setValue(0)
        self.lbl_download_status.setVisible(True)
        self.lbl_download_status.setText("Connecting to Hugging Face model repository...")

        self._download_worker = ModelDownloadWorker(size="small", parent=self)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.start()

    def _on_download_progress(self, pct, done, total, fname):
        self.progress_download_small.setValue(pct)
        mb_done = done / (1024 * 1024)
        mb_total = total / (1024 * 1024)
        self.lbl_download_status.setText(f"Downloading {fname}: {mb_done:.1f} MB / {mb_total:.1f} MB ({pct}%)")

    def _on_download_finished(self, success, message, dest):
        self.btn_download_small.setEnabled(True)
        if success:
            self.btn_download_small.setVisible(False)
            self.progress_download_small.setVisible(False)
            self.lbl_download_status.setVisible(False)
            self._on_language_model_guidance()
        else:
            self.btn_download_small.setText("Retry Download")
            self.lbl_download_status.setText(f"Download error: {message}")
            self.lbl_download_status.setStyleSheet("font-size: 11px; color: #EF4444;")

    # --- SAVE ---

    def _save_settings(self):
        if not self._test_current_hotkey():
            QMessageBox.warning(self, "Shortcut Unavailable", self.lbl_hotkey_status.text())
            return
        # Audio device selection (Feature 28)
        selected_mic = self.combo_mic.currentData()
        if isinstance(selected_mic, dict):
            self.config["audio_input_selection"] = selected_mic
            from engine.audio_devices import resolve_audio_input
            res = resolve_audio_input(selected_mic)
            self.config["audio_device_index"] = res.device_index
        else:
            self.config["audio_device_index"] = selected_mic
            from engine.audio_devices import build_device_selection
            self.config["audio_input_selection"] = build_device_selection(selected_mic)
        self.config["ui_theme"] = self.combo_ui_theme.currentData()
        model_text = self.combo_model.currentText()
        if "tiny" in model_text:
            self.config["local_model_size"] = "tiny"
        elif "base" in model_text:
            self.config["local_model_size"] = "base"
        elif "small" in model_text:
            self.config["local_model_size"] = "small"
        elif "medium" in model_text:
            self.config["local_model_size"] = "medium"

        # Language code
        lang_idx = self.combo_lang.currentIndex()
        if lang_idx >= 0:
            self.config["language"] = self.combo_lang.itemData(lang_idx)

        # Tone / Writing mode key
        idx = self.combo_tone.currentIndex()
        if 0 <= idx < len(self.tone_options):
            self.config["active_tone_mode"] = self.tone_options[idx][0]

        self.config["hotkey"] = self.combo_shortcut.currentText().strip()
        self.config["hotkey_exclusive"] = True
        self.config["hotkey_mode"] = "push_to_talk" if self.radio_ptt.isChecked() else "toggle"
        self.config["ducking_enabled"] = self.chk_ducking.isChecked()
        self.config["sound_effects_enabled"] = self.chk_sound.isChecked()
        
        # Save personalization items
        self.personalization.save()
        
        if self.on_save(self.config) is False:
            QMessageBox.warning(self, "Settings Not Applied", "FlowPilot could not apply the selected shortcut. Please choose another key.")
            return
        if self.embedded:
            self.save_status.setText("Settings saved and applied.")
        else:
            QMessageBox.information(self, "Saved", "FlowPilot settings and personalization updated successfully!")
            self.close()
