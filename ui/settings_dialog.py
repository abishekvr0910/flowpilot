"""
FlowPilot Settings & Personalization Dialog
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
    QTextEdit, QFileDialog, QSplitter, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import pyperclip
import json

from engine.language_registry import LanguageRegistry
from engine.personalization import PersonalizationEngine
from engine.hotkey_service import Win32HotkeyService

class SettingsDialog(QDialog):
    def __init__(
        self,
        config: Dict[str, Any],
        on_save: Callable[[Dict[str, Any]], None],
        personalization: Optional[PersonalizationEngine] = None,
        parent=None
    ):
        super().__init__(parent)
        self.config = dict(config)
        self.on_save = on_save
        self.personalization = personalization or PersonalizationEngine()
        self.setWindowTitle("FlowPilot - Settings & Personalization")
        self.resize(760, 640)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
            }
            QTabWidget::pane {
                border: 1px solid #334155;
                background: #1E293B;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #0F172A;
                color: #94A3B8;
                padding: 10px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: #1E293B;
                color: #38BDF8;
                border-bottom: 2px solid #38BDF8;
            }
            QLabel {
                color: #F8FAFC;
                font-size: 13px;
            }
            QLineEdit, QTextEdit {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QComboBox {
                background-color: #334155;
                color: #F8FAFC;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QCheckBox, QRadioButton {
                color: #F8FAFC;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 1px solid #475569;
                background: #0F172A;
            }
            QRadioButton::indicator:checked {
                background-color: #38BDF8;
                border: 2px solid #0F172A;
            }
            QPushButton {
                background-color: #0284C7;
                color: white;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
            QTableWidget {
                background-color: #0F172A;
                color: #F8FAFC;
                gridline-color: #334155;
                border: 1px solid #334155;
                border-radius: 6px;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #1E293B;
                color: #94A3B8;
                padding: 6px;
                border: 1px solid #334155;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout(self)

        tabs = QTabWidget(self)
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_personalization_tab(), "Personalization")
        tabs.addTab(self._build_history_tab(), "Dictation History")
        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_save = QPushButton("Save & Apply", self)
        btn_save.clicked.connect(self._save_settings)
        btn_layout.addWidget(btn_save)

        btn_close = QPushButton("Close", self)
        btn_close.setStyleSheet("background-color: #475569;")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def _build_general_tab(self) -> QWidget:
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setContentsMargins(20, 20, 20, 20)
        vbox.setSpacing(14)

        # STT Model
        lbl_model = QLabel("Local Speech Recognition Model (Faster-Whisper):")
        vbox.addWidget(lbl_model)
        self.combo_model = QComboBox()
        self.combo_model.addItems([
            "tiny (Fastest, ~75MB)",
            "base (Balanced ultra-fast, ~140MB - Recommended)",
            "small (High accuracy, ~460MB)",
            "medium (Maximum precision, ~1.4GB)"
        ])
        current_model = self.config.get("local_model_size", "base")
        for i in range(self.combo_model.count()):
            if current_model in self.combo_model.itemText(i):
                self.combo_model.setCurrentIndex(i)
                break
        vbox.addWidget(self.combo_model)

        # Primary Language Selector (from LanguageRegistry)
        lbl_lang = QLabel("Speech Language & Script:")
        vbox.addWidget(lbl_lang)
        self.combo_lang = QComboBox()
        languages = LanguageRegistry.list_supported_languages()
        cur_lang = self.config.get("language", "auto")
        selected_lang_idx = 0
        for idx, lang in enumerate(languages):
            display_str = f"{lang['name']} ({lang['native_name']}) [{lang['code']}]"
            self.combo_lang.addItem(display_str, lang["code"])
            if lang["code"] == cur_lang:
                selected_lang_idx = idx
        self.combo_lang.setCurrentIndex(selected_lang_idx)
        vbox.addWidget(self.combo_lang)

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
        for key, label in self.tone_options:
            self.combo_tone.addItem(label, key)
        cur_mode = self.config.get("active_tone_mode", "developer")
        for i, (key, _) in enumerate(self.tone_options):
            if key == cur_mode:
                self.combo_tone.setCurrentIndex(i)
                break
        vbox.addWidget(self.combo_tone)

        # Dictation Mode (Toggle vs Push-to-Talk)
        lbl_mode = QLabel("Dictation Trigger Mode:")
        vbox.addWidget(lbl_mode)
        
        mode_layout = QHBoxLayout()
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
            "Ctrl+Shift+Space",
            "Ctrl+Alt+Space",
            "F9",
            "F8",
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
            "Global Shortcut Architecture:\n"
            "• Default Toggle: Ctrl + Shift + Space (Instant conflict-free toggle from any app)\n"
            "• Single-Key Push-to-Talk: F9 (Seamless hold-to-speak without modifier clutter)\n"
            "• Note on Ctrl+Win: Windows 11 kernel intercepts raw Ctrl+Win (Win32 vk=0 cannot dispatch WM_HOTKEY) "
            "and reserves Win+Ctrl+Space for IME/Emoji switching. FlowPilot provides reliable, collision-free shortcuts "
            "that work side-by-side with any existing desktop tools."
        )
        lbl_hotkeys.setStyleSheet("color: #94A3B8; background: #0F172A; padding: 10px; border-radius: 6px; font-size: 11px; line-height: 1.4;")
        vbox.addWidget(lbl_hotkeys)

        vbox.addStretch()
        return widget

    def _build_personalization_tab(self) -> QWidget:
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(12)

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
            self.table_dict.setItem(r, 1, QTableWidgetItem(item.get("alias", "")))

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
        self.personalization.add_term(term, alias)
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
            return
        cur_hk = self.config.get("hotkey", "")
        avail, msg = Win32HotkeyService.test_hotkey_availability(hk, currently_active_hotkey=cur_hk)
        if avail:
            self.lbl_hotkey_status.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px;")
            self.lbl_hotkey_status.setText(f"[AVAILABLE] {msg}")
        else:
            self.lbl_hotkey_status.setStyleSheet("color: #EF4444; font-weight: bold; font-size: 12px;")
            self.lbl_hotkey_status.setText(f"[CONFLICT/INVALID] {msg}")

    # --- SAVE ---

    def _save_settings(self):
        # STT model size
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
        self.config["hotkey_mode"] = "push_to_talk" if self.radio_ptt.isChecked() else "toggle"
        self.config["ducking_enabled"] = self.chk_ducking.isChecked()
        self.config["sound_effects_enabled"] = self.chk_sound.isChecked()
        
        # Save personalization items
        self.personalization.save()
        
        self.on_save(self.config)
        QMessageBox.information(self, "Saved", "FlowPilot settings and personalization updated successfully!")
        self.close()
