"""
FlowPilot Custom Dictionary & Technical Vocabulary Hub View
Provides a dedicated, discoverable surface to manage custom terms, technical identifiers,
proper names, and phonetic pronunciations for speech recognition biasing.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
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
        lbl_subtitle = QLabel("Train the local engine on proprietary identifiers, code symbols, and proper nouns without cloud egress.")
        lbl_subtitle.setStyleSheet("font-size: 13px; color: #94A3B8;")
        header_box.addWidget(lbl_title)
        header_box.addWidget(lbl_subtitle)
        layout.addLayout(header_box)

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
        add_layout = QHBoxLayout(card_add)
        add_layout.setContentsMargins(12, 10, 12, 10)
        add_layout.setSpacing(12)

        self.input_term = QLineEdit()
        self.input_term.setPlaceholderText("Exact written term (e.g. Kubernetes, FastAPI, SHA-256)")
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
        self.input_alias.setPlaceholderText("Spoken phonetic hint (e.g. koober nettees, fast api)")
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

        btn_add = QPushButton("+ Add to Dictionary")
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 13px;
                padding: 9px 18px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #1D4ED8; }
            QPushButton:pressed { background-color: #1E40AF; }
        """)
        btn_add.clicked.connect(self._on_add_term)

        add_layout.addWidget(self.input_term, 2)
        add_layout.addWidget(self.input_alias, 2)
        add_layout.addWidget(btn_add, 1)
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
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Target Term / Code Symbol", "Spoken Phonetic Alias", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 90)
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
        query = self.input_search.text().strip().lower()
        self.table.setRowCount(0)
        terms = self.personalization.dictionary
        filtered = []
        for item in terms:
            t = item.get("term", "")
            a = item.get("alias", "")
            if not query or query in t.lower() or query in a.lower():
                filtered.append((t, a))
        self.table.setRowCount(len(filtered))

        for row, (term, alias) in enumerate(filtered):
            item_term = QTableWidgetItem(term)
            item_term.setForeground(QColor("#38BDF8"))
            item_alias = QTableWidgetItem(alias)
            item_alias.setForeground(QColor("#CBD5E1"))

            btn_del = QPushButton("Delete")
            btn_del.setStyleSheet("background-color: #7F1D1D; color: #FCA5A5; border: none; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;")
            btn_del.clicked.connect(lambda _, t=term: self._on_delete_term(t))

            self.table.setItem(row, 0, item_term)
            self.table.setItem(row, 1, item_alias)
            self.table.setCellWidget(row, 2, btn_del)

        self.lbl_count.setText(f"{len(filtered)} custom term{'s' if len(filtered) != 1 else ''}")

    def _on_search_changed(self, text: str):
        self.reload_dictionary()

    def _on_add_term(self):
        term = self.input_term.text().strip()
        alias = self.input_alias.text().strip()
        if not term:
            QMessageBox.warning(self, "Invalid Term", "Please provide a valid term or symbol name.")
            return
        self.personalization.add_term(term, alias)
        self.personalization.save()
        self.input_term.clear()
        self.input_alias.clear()
        self.reload_dictionary()

    def _on_delete_term(self, term: str):
        self.personalization.remove_term(term)
        self.personalization.save()
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
