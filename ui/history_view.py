"""
FlowPilot Dictation History & Audio Replay Vault View (100% Offline & Private)
Native PySide6 interface for reviewing past dictations:
- Real-time search across transcripts, dates, and applications
- Audio Replay Vault: listen back to original recordings (▷ / ⏹)
- Bookmark favorite transcriptions (⭐)
- One-click copy, deletion, and export
- Circular retention controls
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QScrollArea, QFrame, QMessageBox, QFileDialog, QComboBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
import pyperclip

from engine.history_vault import get_history_vault, HistoryVaultEngine


class HistoryItemWidget(QFrame):
    def __init__(self, item: Dict[str, Any], vault: HistoryVaultEngine, on_changed: callable, parent=None):
        super().__init__(parent)
        self.item = item
        self.vault = vault
        self.on_changed = on_changed
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame:hover {
                border: 1px solid #334155;
                background-color: #131E33;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header: Metadata badges & Action buttons
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        app_badge = QLabel(f"📱 {self.item.get('target_app', 'Desktop')}")
        app_badge.setStyleSheet("""
            background-color: #1E293B;
            color: #38BDF8;
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 4px;
        """)
        hdr.addWidget(app_badge)

        dt_lbl = QLabel(self.item.get("datetime", ""))
        dt_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        hdr.addWidget(dt_lbl)

        dur_lbl = QLabel(f"⏱ {self.item.get('duration_sec', 0)}s • {self.item.get('word_count', 0)} words")
        dur_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        hdr.addWidget(dur_lbl)

        hdr.addStretch()

        # Audio Replay Button
        has_audio = bool(self.item.get("audio_file"))
        self.btn_play = QPushButton("▷ Replay Audio" if has_audio else "No Audio")
        self.btn_play.setEnabled(has_audio)
        self.btn_play.setStyleSheet(self._btn_style(primary=has_audio))
        if has_audio:
            self.btn_play.clicked.connect(self._toggle_audio_play)
        hdr.addWidget(self.btn_play)

        # Star / Bookmark button
        is_star = bool(self.item.get("bookmarked"))
        self.btn_star = QPushButton("⭐ Starred" if is_star else "☆ Star")
        self.btn_star.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #FACC15;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.btn_star.clicked.connect(self._toggle_bookmark)
        hdr.addWidget(self.btn_star)

        # Copy button
        btn_copy = QPushButton("📋 Copy")
        btn_copy.setStyleSheet(self._btn_style())
        btn_copy.clicked.connect(self._copy_text)
        hdr.addWidget(btn_copy)

        # Delete button
        btn_del = QPushButton("🗑")
        btn_del.setToolTip("Delete entry")
        btn_del.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94A3B8;
                border: none;
                font-size: 12px;
                padding: 3px 6px;
            }
            QPushButton:hover {
                color: #EF4444;
            }
        """)
        btn_del.clicked.connect(self._delete_entry)
        hdr.addWidget(btn_del)

        layout.addLayout(hdr)

        # Body: Formatted transcription text
        txt = QLabel(self.item.get("formatted_text", ""))
        txt.setWordWrap(True)
        txt.setTextInteractionFlags(Qt.TextSelectableByMouse)
        txt.setStyleSheet("color: #F8FAFC; font-size: 13px; line-height: 1.5; padding: 4px 0;")
        layout.addWidget(txt)

    def _btn_style(self, primary: bool = False) -> str:
        bg = "#0284C7" if primary else "#1E293B"
        hover = "#0369A1" if primary else "#334155"
        color = "#FFFFFF" if primary else "#94A3B8"
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {hover};
                color: #F8FAFC;
            }}
        """

    def _toggle_audio_play(self):
        eid = self.item.get("id")
        if self.vault.is_playing and self.vault.playing_id == eid:
            self.vault.stop_audio()
            self.btn_play.setText("▷ Replay Audio")
        else:
            self.btn_play.setText("⏹ Stop Audio")
            ok = self.vault.play_audio(eid, on_finished=self._on_play_done)
            if not ok:
                self.btn_play.setText("▷ Replay Audio")

    def _on_play_done(self):
        self.btn_play.setText("▷ Replay Audio")

    def _toggle_bookmark(self):
        eid = self.item.get("id")
        new_val = self.vault.toggle_bookmark(eid)
        self.item["bookmarked"] = new_val
        self.btn_star.setText("⭐ Starred" if new_val else "☆ Star")
        if self.on_changed:
            self.on_changed()

    def _copy_text(self):
        text = self.item.get("formatted_text", "")
        if text:
            pyperclip.copy(text)

    def _delete_entry(self):
        eid = self.item.get("id")
        self.vault.delete_entry(eid)
        if self.on_changed:
            self.on_changed()


class HistoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vault: HistoryVaultEngine = get_history_vault()
        self._star_filter = False
        self._init_ui()
        self.reload_history()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header Bar
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("Dictation History & Audio Vault")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #F8FAFC;")
        lbl_sub = QLabel("Search past transcripts, replay recorded audio locally, and manage starred notes.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)

        header.addStretch()

        self.btn_star_filter = QPushButton("⭐ Starred Only")
        self.btn_star_filter.setCheckable(True)
        self.btn_star_filter.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:checked {
                background-color: #78350F;
                color: #FDE68A;
                border: 1px solid #F59E0B;
            }
        """)
        self.btn_star_filter.clicked.connect(self._toggle_star_filter)
        header.addWidget(self.btn_star_filter)

        btn_export = QPushButton("💾 Export...")
        btn_export.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #38BDF8;
            }
        """)
        btn_export.clicked.connect(self._export_history)
        header.addWidget(btn_export)

        btn_clear = QPushButton("🧹 Clear Old")
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #EF4444;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #7F1D1D;
                color: #FCA5A5;
            }
        """)
        btn_clear.clicked.connect(self._clear_history)
        header.addWidget(btn_clear)

        layout.addLayout(header)

        # Search Bar
        search_row = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search transcripts by keyword, application, or date...")
        self.txt_search.setStyleSheet("""
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
        self.txt_search.textChanged.connect(self.reload_history)
        search_row.addWidget(self.txt_search)
        layout.addLayout(search_row)

        # Scroll Area for feed
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
        """)

        self.feed_container = QWidget()
        self.feed_layout = QVBoxLayout(self.feed_container)
        self.feed_layout.setContentsMargins(8, 8, 8, 8)
        self.feed_layout.setSpacing(8)
        self.feed_layout.addStretch()

        self.scroll.setWidget(self.feed_container)
        layout.addWidget(self.scroll, stretch=1)

        # Status footer
        self.lbl_count = QLabel("0 dictation sessions recorded")
        self.lbl_count.setStyleSheet("color: #64748B; font-size: 12px;")
        layout.addWidget(self.lbl_count)

    def _toggle_star_filter(self):
        self._star_filter = self.btn_star_filter.isChecked()
        self.reload_history()

    def reload_history(self):
        # Clear existing items
        while self.feed_layout.count() > 1:
            child = self.feed_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        query = self.txt_search.text().strip()
        entries = self.vault.list_entries(query=query, bookmark_only=self._star_filter)

        self.lbl_count.setText(f"Showing {len(entries)} dictation sessions")

        if not entries:
            empty_lbl = QLabel("No dictations found matching query.")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #64748B; font-size: 13px; padding: 40px;")
            self.feed_layout.insertWidget(0, empty_lbl)
            return

        for item in entries:
            w = HistoryItemWidget(item, self.vault, on_changed=self.reload_history)
            self.feed_layout.insertWidget(self.feed_layout.count() - 1, w)

    def _export_history(self):
        entries = self.vault.list_entries()
        if not entries:
            QMessageBox.information(self, "Export", "History is currently empty.")
            return

        dest_file, _ = QFileDialog.getSaveFileName(
            self, "Export Dictation History", "flowpilot_history.md", "Markdown (*.md);;JSON (*.json)"
        )
        if not dest_file:
            return

        try:
            if dest_file.endswith(".json"):
                import json
                with open(dest_file, "w", encoding="utf-8") as f:
                    json.dump(entries, f, indent=2, ensure_ascii=False)
            else:
                lines = ["# FlowPilot Dictation History\n\n"]
                for e in entries:
                    lines.append(f"### {e.get('datetime', '')} ({e.get('target_app', '')})\n")
                    lines.append(f"{e.get('formatted_text', '')}\n\n---\n\n")
                with open(dest_file, "w", encoding="utf-8") as f:
                    f.writelines(lines)
            QMessageBox.information(self, "Export Complete", f"Exported {len(entries)} items to {dest_file}")
        except Exception as err:
            QMessageBox.critical(self, "Export Failed", f"Error saving file: {err}")

    def _clear_history(self):
        reply = QMessageBox.question(
            self, "Clear History",
            "Are you sure you want to clear un-starred history?\nStarred items will be preserved.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            count = self.vault.clear_all(keep_bookmarks=True)
            self.reload_history()
            QMessageBox.information(self, "Cleared", f"Cleared {count} past dictations.")
