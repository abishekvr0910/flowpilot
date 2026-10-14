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
    QTextEdit, QFileDialog, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import pyperclip
import json

from engine.language_registry import LanguageRegistry
from engine.personalization import PersonalizationEngine

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
        self.resize(750, 560)
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
            QCheckBox {
                color: #F8FAFC;
                font-size: 13px;
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

        # Primary Shortcut Selector
        lbl_shortcut = QLabel("Primary Global Keyboard Shortcut:")
        vbox.addWidget(lbl_shortcut)
        self.combo_shortcut = QComboBox()
        self.combo_shortcut.addItems(["Ctrl+Shift+Space", "Ctrl+Alt+Space", "F9", "F8"])
        cur_hk = self.config.get("hotkey", "Ctrl+Shift+Space").replace("<", "").replace(">", "").strip()
        self.combo_shortcut.setCurrentText(cur_hk)
        vbox.addWidget(self.combo_shortcut)

        # Audio Ducking Checkbox
        self.chk_ducking = QCheckBox("Silence background music / video while dictating")
        self.chk_ducking.setChecked(True)
        vbox.addWidget(self.chk_ducking)

        # Audio Feedback Chimes Checkbox
        self.chk_sound = QCheckBox("Play audible chimes when dictation starts, stops, or cancels")
        self.chk_sound.setChecked(self.config.get("sound_effects_enabled", True))
        vbox.addWidget(self.chk_sound)

        # Hotkey safety banner
        lbl_hotkeys = QLabel("Configured Global Hotkeys:\n• Primary:  Ctrl + Shift + Space\n• Secondary: Ctrl + Alt + Space\n• Single-Key: F9\n(Wispr Flow's Ctrl + Win is intentionally avoided to prevent Windows OS collisions)")
        lbl_hotkeys.setStyleSheet("color: #94A3B8; background: #0F172A; padding: 10px; border-radius: 6px; font-size: 11px;")
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

        self.config["hotkey"] = self.combo_shortcut.currentText()
        self.config["sound_effects_enabled"] = self.chk_sound.isChecked()
        
        # Save personalization items
        self.personalization.save()
        
        self.on_save(self.config)
        QMessageBox.information(self, "Saved", "FlowPilot settings and personalization updated successfully!")
        self.close()
