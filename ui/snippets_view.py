"""
FlowPilot Voice Snippets & Text Expansions Hub View
Provides a dedicated, discoverable surface to manage spoken macro triggers
and their corresponding multiline boilerplate text or markdown expansions.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from engine.personalization import PersonalizationEngine


class SnippetsView(QWidget):
    def __init__(self, parent=None, personalization: Optional[PersonalizationEngine] = None):
        super().__init__(parent)
        self.personalization = personalization or PersonalizationEngine()
        self._init_ui()
        self.reload_snippets()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        lbl_title = QLabel("⚡ Voice Snippets & Boilerplate Expansions")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #F8FAFC;")
        lbl_subtitle = QLabel("Speak a short trigger phrase to automatically expand into lengthy boilerplate, meeting links, or email templates.")
        lbl_subtitle.setStyleSheet("font-size: 13px; color: #94A3B8;")
        header_box.addWidget(lbl_title)
        header_box.addWidget(lbl_subtitle)
        layout.addLayout(header_box)

        # Add Snippet Card
        card_add = QFrame()
        card_add.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 10px;
                padding: 14px;
            }
        """)
        add_layout = QVBoxLayout(card_add)
        add_layout.setContentsMargins(12, 10, 12, 10)
        add_layout.setSpacing(10)

        top_row = QHBoxLayout()
        self.input_trigger = QLineEdit()
        self.input_trigger.setPlaceholderText("Spoken Trigger Phrase (e.g. insert meeting link, my bio, standup update)")
        self.input_trigger.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
        """)
        top_row.addWidget(self.input_trigger, 3)

        btn_add = QPushButton("+ Add Snippet")
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
        btn_add.clicked.connect(self._on_add_snippet)
        top_row.addWidget(btn_add, 1)
        add_layout.addLayout(top_row)

        self.input_expansion = QPlainTextEdit()
        self.input_expansion.setPlaceholderText("Expanded text or markdown template inserted when the trigger phrase is spoken...")
        self.input_expansion.setFixedHeight(64)
        self.input_expansion.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
        """)
        add_layout.addWidget(self.input_expansion)
        layout.addWidget(card_add)

        # Search Bar & Count
        filter_box = QHBoxLayout()
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("🔍 Filter voice snippets...")
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

        self.lbl_count = QLabel("0 snippets")
        self.lbl_count.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 600;")
        filter_box.addWidget(self.lbl_count)
        layout.addLayout(filter_box)

        # Snippets Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Spoken Trigger Phrase", "Expanded Replacement Text", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 200)
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

    def reload_snippets(self):
        query = self.input_search.text().strip().lower()
        self.table.setRowCount(0)
        snips = self.personalization.snippets
        filtered = []
        for item in snips:
            tr = item.get("trigger", "")
            ex = item.get("expansion", "")
            if not query or query in tr.lower() or query in ex.lower():
                filtered.append((tr, ex))
        self.table.setRowCount(len(filtered))

        for row, (trig, exp) in enumerate(filtered):
            item_trig = QTableWidgetItem(trig)
            item_trig.setForeground(QColor("#38BDF8"))
            item_exp = QTableWidgetItem(exp)
            item_exp.setForeground(QColor("#E2E8F0"))

            btn_del = QPushButton("Delete")
            btn_del.setStyleSheet("background-color: #7F1D1D; color: #FCA5A5; border: none; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;")
            btn_del.clicked.connect(lambda _, t=trig: self._on_delete_snippet(t))

            self.table.setItem(row, 0, item_trig)
            self.table.setItem(row, 1, item_exp)
            self.table.setCellWidget(row, 2, btn_del)

        self.lbl_count.setText(f"{len(filtered)} snippet{'s' if len(filtered) != 1 else ''}")

    def _on_search_changed(self, text: str):
        self.reload_snippets()

    def _on_add_snippet(self):
        trig = self.input_trigger.text().strip()
        exp = self.input_expansion.toPlainText().strip()
        if not trig or not exp:
            QMessageBox.warning(self, "Invalid Snippet", "Please specify both a spoken trigger phrase and expansion text.")
            return
        self.personalization.add_snippet(trig, exp)
        self.personalization.save()
        self.input_trigger.clear()
        self.input_expansion.clear()
        self.reload_snippets()

    def _on_delete_snippet(self, trig: str):
        self.personalization.remove_snippet(trig)
        self.personalization.save()
        self.reload_snippets()

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Snippets JSON", "", "JSON Files (*.json)")
        if path:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if self.personalization.import_json(content, merge=True):
                self.personalization.save()
                self.reload_snippets()
                QMessageBox.information(self, "Imported", "Voice snippets imported successfully!")

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Snippets JSON", "flowpilot_snippets.json", "JSON Files (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.personalization.export_json())
            QMessageBox.information(self, "Exported", f"Exported snippets to {path}")
