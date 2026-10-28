"""
FlowPilot Custom Dictionary & Technical Vocabulary Hub View (PR 3)
Provides a dedicated, discoverable surface to manage custom terms, technical identifiers,
proper names, and multi-alias phonetic pronunciations for speech recognition biasing.
Supports language scoping (English, Hindi, Tamil, Malayalam) and application profile scoping.
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from engine.personalization import PersonalizationEngine


class DictionaryView(QWidget):
    def __init__(self, parent=None, personalization: Optional[PersonalizationEngine] = None):
        super().__init__(parent)
        self.personalization = personalization or PersonalizationEngine()
        self._init_ui()
        self.reload_dictionary()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        lbl_title = QLabel("📖 Custom Dictionary & Technical Glossary")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #F8FAFC;")
        lbl_subtitle = QLabel("Teach the local engine proprietary identifiers, code symbols, and phonetic aliases without cloud egress.")
        lbl_subtitle.setStyleSheet("font-size: 13px; color: #94A3B8;")
        header_box.addWidget(lbl_title)
        header_box.addWidget(lbl_subtitle)
        layout.addLayout(header_box)

        # Suggestions Container (Auto-learned vocabulary from user corrections)
        self.card_suggestions = QFrame()
        self.card_suggestions.setStyleSheet("""
            QFrame {
                background-color: #172554;
                border: 1px solid #1E40AF;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        self.suggestions_vbox = QVBoxLayout(self.card_suggestions)
        self.suggestions_vbox.setContentsMargins(12, 10, 12, 10)
        self.suggestions_vbox.setSpacing(8)
        self.card_suggestions.setVisible(False)
        layout.addWidget(self.card_suggestions)

        # Add Term Card
        card_add = QFrame()
        card_add.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 10px;
                padding: 14px;
            }
        """)
        add_vbox = QVBoxLayout(card_add)
        add_vbox.setContentsMargins(12, 10, 12, 10)
        add_vbox.setSpacing(10)

        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(12)

        self.input_term = QLineEdit()
        self.input_term.setPlaceholderText("Exact written term (e.g. Kubernetes, FastAPI, SHA-256, வணக்கம்)")
        self.input_term.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
        """)

        self.input_alias = QLineEdit()
        self.input_alias.setPlaceholderText("Spoken phonetic hints (comma-separated, e.g. koober nettees, k8s)")
        self.input_alias.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
        """)

        row1_layout.addWidget(self.input_term, 3)
        row1_layout.addWidget(self.input_alias, 3)
        add_vbox.addLayout(row1_layout)

        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(12)

        lbl_lang = QLabel("Language:")
        lbl_lang.setStyleSheet("color: #94A3B8; font-size: 12px;")
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["Global (All Languages)", "English (en)", "Hindi (hi)", "Tamil (ta)", "Malayalam (ml)"])
        self.combo_lang.setStyleSheet("""
            QComboBox {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
        """)

        lbl_profile = QLabel("Scope:")
        lbl_profile.setStyleSheet("color: #94A3B8; font-size: 12px;")
        self.combo_profile = QComboBox()
        self.combo_profile.addItems(["Global (All Apps)", "Developer", "Terminal", "Email", "Chat"])
        self.combo_profile.setStyleSheet("""
            QComboBox {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
        """)

        btn_add = QPushButton("+ Add to Dictionary")
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 13px;
                padding: 8px 18px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #1D4ED8; }
            QPushButton:pressed { background-color: #1E40AF; }
        """)
        btn_add.clicked.connect(self._on_add_term)

        row2_layout.addWidget(lbl_lang)
        row2_layout.addWidget(self.combo_lang, 2)
        row2_layout.addWidget(lbl_profile)
        row2_layout.addWidget(self.combo_profile, 2)
        row2_layout.addStretch(1)
        row2_layout.addWidget(btn_add, 2)
        add_vbox.addLayout(row2_layout)

        layout.addWidget(card_add)

        # Search Bar & Count
        filter_box = QHBoxLayout()
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("🔍 Filter dictionary words...")
        self.input_search.setStyleSheet("""
            QLineEdit {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #1E293B;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 13px;
            }
        """)
        self.input_search.textChanged.connect(self._on_search_changed)
        filter_box.addWidget(self.input_search)

        self.lbl_count = QLabel("0 terms")
        self.lbl_count.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 600;")
        filter_box.addWidget(self.lbl_count)
        layout.addLayout(filter_box)

        # Dictionary Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Target Term / Code Symbol", "Spoken Phonetic Aliases", "Language", "Scope", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 90)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #1E293B;
                border-radius: 8px;
                gridline-color: #1E293B;
                selection-background-color: #1E293B;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #1E293B;
                color: #94A3B8;
                padding: 8px;
                font-weight: 600;
                font-size: 12px;
                border: none;
            }
        """)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # Bottom Actions: Import, Export
        btn_bar = QHBoxLayout()
        btn_import = QPushButton("📥 Import JSON")
        btn_import.setStyleSheet("background-color: #1E293B; color: #CBD5E1; border: 1px solid #334155; padding: 7px 14px; border-radius: 6px; font-weight: 600;")
        btn_import.clicked.connect(self._on_import)

        btn_export = QPushButton("📤 Export JSON")
        btn_export.setStyleSheet("background-color: #1E293B; color: #CBD5E1; border: 1px solid #334155; padding: 7px 14px; border-radius: 6px; font-weight: 600;")
        btn_export.clicked.connect(self._on_export)

        btn_bar.addWidget(btn_import)
        btn_bar.addWidget(btn_export)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

    def reload_dictionary(self):
        # Auto-learned suggestions from user manual corrections
        try:
            from engine.writing_intelligence import get_correction_detector
            suggestions = get_correction_detector().get_pending_suggestions()
        except Exception:
            suggestions = []

        while self.suggestions_vbox.count():
            item = self.suggestions_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if suggestions:
            self.card_suggestions.setVisible(True)
            lbl_sugg_title = QLabel(f"💡 Auto-Detected Vocabulary ({len(suggestions)}) — Learned from your manual corrections:")
            lbl_sugg_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #93C5FD;")
            self.suggestions_vbox.addWidget(lbl_sugg_title)

            for s in suggestions:
                s_row = QHBoxLayout()
                heard_txt = s.get("heard", "")
                corr_txt = s.get("corrected", "")
                occ = s.get("occurrences", 2)

                lbl_desc = QLabel(f"<b>{corr_txt}</b>  (heard as <i>'{heard_txt}'</i>, corrected {occ}×)")
                lbl_desc.setStyleSheet("color: #E2E8F0; font-size: 13px;")

                btn_accept = QPushButton(f"+ Add '{corr_txt}'")
                btn_accept.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 4px 10px; border-radius: 4px; font-size: 11px;")
                btn_accept.clicked.connect(lambda _, h=heard_txt, c=corr_txt: self._on_accept_suggestion(h, c))

                btn_dismiss = QPushButton("Dismiss")
                btn_dismiss.setStyleSheet("background-color: #334155; color: #94A3B8; padding: 4px 8px; border-radius: 4px; font-size: 11px;")
                btn_dismiss.clicked.connect(lambda _, h=heard_txt, c=corr_txt: self._on_dismiss_suggestion(h, c))

                s_row.addWidget(lbl_desc, 1)
                s_row.addWidget(btn_accept)
                s_row.addWidget(btn_dismiss)
                self.suggestions_vbox.addLayout(s_row)
        else:
            self.card_suggestions.setVisible(False)

        query = self.input_search.text().strip().lower()
        self.table.setRowCount(0)
        terms = self.personalization.dictionary
        filtered = []
        for item in terms:
            t = item.get("term", "")
            aliases = item.get("aliases") or ([item["alias"]] if item.get("alias") else [])
            alias_str = ", ".join(aliases)
            lang = item.get("language") or "Global"
            prof = item.get("profile") or "Global"
            if not query or query in t.lower() or query in alias_str.lower() or query in lang.lower() or query in prof.lower():
                filtered.append((t, alias_str, lang, prof))
        self.table.setRowCount(len(filtered))

        for row, (term, alias_str, lang, prof) in enumerate(filtered):
            item_term = QTableWidgetItem(term)
            item_term.setForeground(QColor("#38BDF8"))
            item_alias = QTableWidgetItem(alias_str)
            item_alias.setForeground(QColor("#CBD5E1"))
            item_lang = QTableWidgetItem(lang.upper() if lang != "Global" else "Global")
            item_lang.setForeground(QColor("#A78BFA"))
            item_prof = QTableWidgetItem(prof.capitalize() if prof != "Global" else "Global")
            item_prof.setForeground(QColor("#34D399"))

            btn_del = QPushButton("Delete")
            btn_del.setStyleSheet("background-color: #7F1D1D; color: #FCA5A5; border: none; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;")
            btn_del.clicked.connect(lambda _, t=term: self._on_delete_term(t))

            self.table.setItem(row, 0, item_term)
            self.table.setItem(row, 1, item_alias)
            self.table.setItem(row, 2, item_lang)
            self.table.setItem(row, 3, item_prof)
            self.table.setCellWidget(row, 4, btn_del)

        self.lbl_count.setText(f"{len(filtered)} custom term{'s' if len(filtered) != 1 else ''}")

    def _on_search_changed(self, text: str):
        self.reload_dictionary()

    def _on_add_term(self):
        term = self.input_term.text().strip()
        alias_raw = self.input_alias.text().strip()
        if not term:
            QMessageBox.warning(self, "Invalid Term", "Please provide a valid term or symbol name.")
            return

        aliases: List[str] = [a.strip() for a in alias_raw.split(",") if a.strip()] if alias_raw else []

        lang_idx = self.combo_lang.currentIndex()
        lang_map = {0: None, 1: "en", 2: "hi", 3: "ta", 4: "ml"}
        language = lang_map.get(lang_idx)

        prof_idx = self.combo_profile.currentIndex()
        prof_map = {0: None, 1: "developer", 2: "terminal", 3: "email", 4: "chat"}
        profile = prof_map.get(prof_idx)

        self.personalization.add_term(
            term=term,
            alias=aliases[0] if aliases else "",
            language=language,
            profile=profile,
            aliases=aliases
        )
        self.personalization.save()
        self.input_term.clear()
        self.input_alias.clear()
        self.reload_dictionary()

    def _on_delete_term(self, term: str):
        self.personalization.remove_term(term)
        self.personalization.save()
        self.reload_dictionary()

    def _on_accept_suggestion(self, heard: str, corrected: str):
        self.personalization.add_term(
            term=corrected,
            alias=heard,
            aliases=[heard]
        )
        self.personalization.save()
        try:
            from engine.writing_intelligence import get_correction_detector
            get_correction_detector().dismiss_suggestion(heard, corrected, cooldown_days=365)
        except Exception:
            pass
        self.reload_dictionary()

    def _on_dismiss_suggestion(self, heard: str, corrected: str):
        try:
            from engine.writing_intelligence import get_correction_detector
            get_correction_detector().dismiss_suggestion(heard, corrected, cooldown_days=7)
        except Exception:
            pass
        self.reload_dictionary()

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Dictionary JSON", "", "JSON Files (*.json)")
        if path:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if self.personalization.import_json(content, merge=True):
                self.personalization.save()
                self.reload_dictionary()
                QMessageBox.information(self, "Imported", "Custom terms imported successfully!")

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Dictionary JSON", "flowpilot_dictionary.json", "JSON Files (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.personalization.export_json())
            QMessageBox.information(self, "Exported", f"Exported dictionary to {path}")
