"""
FlowPilot Meeting Notetaker Studio View
Native PySide6 interface for local meeting transcription and summarization:
- Live streaming timestamped transcript
- Real-time action items and decision detection
- One-click copy and markdown report export
"""

from pathlib import Path
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QFileDialog, QMessageBox, QSplitter, QFrame,
    QLineEdit, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer
import pyperclip

from engine.meeting_notetaker import MeetingNotetakerEngine, MeetingSession

class NotetakerView(QWidget):
    def __init__(self, parent=None, notetaker_engine: Optional[MeetingNotetakerEngine] = None):
        super().__init__(parent)
        self.engine = notetaker_engine or MeetingNotetakerEngine(on_segment=self._on_live_segment)
        self._elapsed_seconds = 0
        self._init_ui()

        # Timer for elapsed meeting clock
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._on_clock_tick)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("Meeting Notetaker")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #F8FAFC;")
        lbl_sub = QLabel("Record discussions, extract action items, and generate private offline summaries.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)

        header.addStretch()

        self.lbl_clock = QLabel("00:00")
        self.lbl_clock.setStyleSheet("""
            background-color: #1E293B;
            color: #38BDF8;
            font-size: 16px;
            font-weight: bold;
            font-family: 'Consolas', monospace;
            padding: 6px 14px;
            border-radius: 6px;
            border: 1px solid #334155;
        """)
        header.addWidget(self.lbl_clock)

        self.btn_record = QPushButton("🔴 Start Meeting Recording")
        self.btn_record.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                padding: 8px 18px;
                border-radius: 6px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
        """)
        self.btn_record.clicked.connect(self._toggle_recording)
        header.addWidget(self.btn_record)

        layout.addLayout(header)

        # Splitter: Live Transcript vs. Action Items & Summary
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #334155;
                width: 2px;
            }
        """)

        # Left: Live Transcript
        left_box = QWidget()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(6)

        lbl_live = QLabel("Live Transcript")
        lbl_live.setStyleSheet("font-weight: bold; font-size: 13px; color: #94A3B8;")
        left_layout.addWidget(lbl_live)

        self.transcript_edit = QTextEdit()
        self.transcript_edit.setPlaceholderText("Meeting transcript will stream here with timestamps when you speak or record...")
        self.transcript_edit.setStyleSheet("""
            QTextEdit {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', monospace;
                font-size: 13px;
                line-height: 1.5;
            }
        """)
        left_layout.addWidget(self.transcript_edit)
        splitter.addWidget(left_box)

        # Right: Action Items & Decisions Summary
        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        lbl_summary_title = QLabel("Decisions & Action Items")
        lbl_summary_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #94A3B8;")
        right_layout.addWidget(lbl_summary_title)

        self.summary_edit = QTextEdit()
        self.summary_edit.setPlaceholderText("Action items (e.g. 'I will send the report') and key decisions will be automatically detected and structured here...")
        self.summary_edit.setStyleSheet("""
            QTextEdit {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.5;
            }
        """)
        right_layout.addWidget(self.summary_edit)

        # Action bar under summary
        btn_box = QHBoxLayout()
        btn_copy = QPushButton("📋 Copy Summary")
        btn_copy.setStyleSheet(self._btn_style())
        btn_copy.clicked.connect(self._copy_summary)
        btn_box.addWidget(btn_copy)

        btn_export = QPushButton("💾 Export Report")
        btn_export.setStyleSheet(self._btn_style())
        btn_export.clicked.connect(self._export_report)
        btn_box.addWidget(btn_export)

        right_layout.addLayout(btn_box)
        splitter.addWidget(right_box)

        splitter.setSizes([450, 400])
        layout.addWidget(splitter)

    def _btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                font-weight: 600;
                padding: 7px 14px;
                border-radius: 6px;
                border: 1px solid #334155;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #38BDF8;
            }
        """

    def _toggle_recording(self):
        if not self.engine.is_recording:
            # Start
            self.engine.start_meeting()
            self._elapsed_seconds = 0
            self.lbl_clock.setText("00:00")
            self._clock_timer.start(1000)
            self.btn_record.setText("⏹ Stop & Summarize")
            self.btn_record.setStyleSheet("""
                QPushButton {
                    background-color: #0284C7;
                    color: #FFFFFF;
                    font-weight: bold;
                    padding: 8px 18px;
                    border-radius: 6px;
                    border: none;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #0369A1;
                }
            """)
        else:
            # Stop & Summarize
            self._clock_timer.stop()
            sess = self.engine.stop_meeting()
            self.btn_record.setText("🔴 Start Meeting Recording")
            self.btn_record.setStyleSheet("""
                QPushButton {
                    background-color: #DC2626;
                    color: #FFFFFF;
                    font-weight: bold;
                    padding: 8px 18px;
                    border-radius: 6px;
                    border: none;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #B91C1C;
                }
            """)
            self._render_summary(sess)

    def _on_clock_tick(self):
        self._elapsed_seconds += 1
        m, s = divmod(self._elapsed_seconds, 60)
        h, m = divmod(m, 60)
        self.lbl_clock.setText(f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}")

    def _on_live_segment(self, seg: dict):
        line = f"[{seg['time']}] {seg['text']}\n"
        self.transcript_edit.append(line.strip())

    def append_segment(self, text: str):
        seg = self.engine.add_transcript_segment(text)
        if seg:
            self._on_live_segment(seg)

    def _render_summary(self, session: Optional[MeetingSession]):
        summary = self.engine.generate_summary(session)
        lines = []
        lines.append(f"# {summary['title']}")
        lines.append(f"**Duration:** {summary['duration']} | **Words:** {summary.get('total_words', 0)}\n")

        lines.append("## 📌 Key Decisions")
        if summary["decisions"]:
            for dec in summary["decisions"]:
                lines.append(f"- {dec}")
        else:
            lines.append("- *(No formal decisions explicitly declared)*")
        lines.append("")

        lines.append("## ✅ Action Items")
        if summary["action_items"]:
            for item in summary["action_items"]:
                lines.append(f"- [ ] {item}")
        else:
            lines.append("- *(No action items identified)*")
        lines.append("")

        lines.append("## 📝 Summary Notes")
        if summary["key_points"]:
            for pt in summary["key_points"]:
                lines.append(f"- {pt}")
        else:
            lines.append("- Discussion captured in full transcript.")

        self.summary_edit.setPlainText("\n".join(lines))

    def _copy_summary(self):
        text = self.summary_edit.toPlainText().strip()
        if text:
            pyperclip.copy(text)
            QMessageBox.information(self, "Copied", "Meeting summary copied to clipboard!")

    def _export_report(self):
        full_report = (
            f"{self.summary_edit.toPlainText()}\n\n"
            f"## 📜 Full Transcript\n\n"
            f"{self.transcript_edit.toPlainText()}"
        )
        if not full_report.strip():
            QMessageBox.information(self, "Export", "No meeting data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Meeting Report", str(Path.home() / "meeting_notes.md"), "Markdown (*.md);;Text (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(full_report)
                QMessageBox.information(self, "Exported", f"Saved meeting report to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to save file: {e}")
