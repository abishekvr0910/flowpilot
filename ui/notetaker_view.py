"""
FlowPilot native meeting notetaker workspace.
Native PySide6 interface for offline meeting transcription, structured notes, and library management:
- Left Sidebar: Past Meetings Library with real-time search, metadata badges, rename & delete
- Center Console: Live streaming transcript with [HH:MM:SS] timestamps, audio VU meter, live timer, pause/resume
- Right Intelligence Studio:
    * Tab 1: Executive Summary & Key Decisions
    * Tab 2: Interactive Action Items Checklist (live click-to-complete [x], custom item addition)
    * Tab 3: Live Meeting Minutes Scratchpad
- Export Suite: Copy Markdown, Copy Action Items, Export to .md, .txt, .json
- 100% local, zero egress, zero third-party cloud exposure
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QFileDialog, QMessageBox, QSplitter, QFrame,
    QLineEdit, QListWidget, QListWidgetItem, QTabWidget, QCheckBox,
    QProgressBar, QComboBox, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QFont, QColor
import pyperclip

from engine.meeting_notetaker import MeetingNotetakerEngine, MeetingSession, TEMPLATES


def _parse_decision_lines(summary_text: str) -> List[str]:
    """Extract decision text without leaking Markdown markers into exports."""
    prefix = "- **Decision:** "
    return [line[len(prefix):] for line in summary_text.splitlines() if line.startswith(prefix)]

class NotetakerSignalBridge(QObject):
    segment_received = Signal(dict)
    audio_level_received = Signal(float)

class NotetakerView(QWidget):
    def __init__(self, parent=None, notetaker_engine: Optional[MeetingNotetakerEngine] = None):
        super().__init__(parent)
        self._bridge = NotetakerSignalBridge()
        self._bridge.segment_received.connect(self._handle_live_segment_gui)
        self._bridge.audio_level_received.connect(self._handle_audio_level_gui)

        if notetaker_engine:
            self.engine = notetaker_engine
            self.engine.on_segment = self._bridge.segment_received.emit
            self.engine.on_audio_level = self._bridge.audio_level_received.emit
            if hasattr(self.engine, "_audio_recorder") and self.engine._audio_recorder:
                self.engine._audio_recorder.on_audio_level = self._bridge.audio_level_received.emit
        else:
            self.engine = MeetingNotetakerEngine(
                on_segment=self._bridge.segment_received.emit,
                on_audio_level=self._bridge.audio_level_received.emit
            )
        self._current_meeting_id: Optional[str] = None
        self._elapsed_seconds = 0
        self._action_checkboxes: List[QCheckBox] = []
        self._last_deliberation_data: Optional[Dict[str, Any]] = None

        self._init_ui()

        # Elapsed meeting timer
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._on_clock_tick)


        # Initial load of past meetings
        self._reload_meeting_list()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # -------------------------------------------------------------
        # Left Column: Meeting Library Sidebar
        # -------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setMinimumWidth(0)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
        """)
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(10, 10, 10, 10)
        s_layout.setSpacing(8)

        btn_new_meeting = QPushButton("➕  New Meeting")
        btn_new_meeting.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                padding: 9px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        btn_new_meeting.clicked.connect(self._on_new_meeting_clicked)
        s_layout.addWidget(btn_new_meeting)

        self.txt_search_meetings = QLineEdit()
        self.txt_search_meetings.setPlaceholderText("🔍 Search meetings...")
        self.txt_search_meetings.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #38BDF8;
            }
        """)
        self.txt_search_meetings.textChanged.connect(self._filter_meeting_list)
        s_layout.addWidget(self.txt_search_meetings)

        lbl_recent = QLabel("PAST SESSIONS")
        lbl_recent.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748B; margin-top: 4px;")
        s_layout.addWidget(lbl_recent)

        self.meeting_list = QListWidget()
        self.meeting_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                color: #F8FAFC;
            }
            QListWidget::item {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px;
                margin-bottom: 6px;
            }
            QListWidget::item:hover {
                border: 1px solid #38BDF8;
                background-color: #243247;
            }
            QListWidget::item:selected {
                border: 1px solid #38BDF8;
                background-color: #0369A1;
            }
        """)
        self.meeting_list.itemClicked.connect(self._on_meeting_selected)
        self.meeting_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.meeting_list.customContextMenuRequested.connect(self._show_meeting_context_menu)
        s_layout.addWidget(self.meeting_list, stretch=1)

        # Three focused tabs keep controls legible inside the dashboard's
        # persistent navigation rail, including at the minimum window size.
        self.workspace_tabs = QTabWidget(self)
        self.workspace_tabs.setObjectName("MeetingWorkspaceTabs")

        # -------------------------------------------------------------
        # Center Console: Live Transcript & Recording
        # -------------------------------------------------------------
        center_box = QWidget()
        c_layout = QVBoxLayout(center_box)
        c_layout.setContentsMargins(4, 0, 8, 0)
        c_layout.setSpacing(10)

        # Meeting Title & Template Header
        header_row = QHBoxLayout()
        self.txt_title = QLineEdit("Team Discussion & Notes")
        self.txt_title.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                color: #F8FAFC;
                font-size: 18px;
                font-weight: bold;
                border: none;
                border-bottom: 2px solid #334155;
                padding: 4px 0;
            }
            QLineEdit:focus {
                border-bottom: 2px solid #38BDF8;
            }
        """)
        header_row.addWidget(self.txt_title, stretch=1)

        self.combo_template = QComboBox()
        self.combo_template.setStyleSheet("""
            QComboBox {
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 12px;
            }
        """)
        for k, v in TEMPLATES.items():
            self.combo_template.addItem(v["name"], k)
        header_row.addWidget(self.combo_template)

        self.btn_translate = QPushButton("🌐 Translate: OFF")
        self.btn_translate.setCheckable(True)
        self.btn_translate.setToolTip("Toggle real-time Faster-Whisper translation to English")
        self.btn_translate.setStyleSheet(self._btn_style())
        self.btn_translate.clicked.connect(self._toggle_translation)
        header_row.addWidget(self.btn_translate)

        self.btn_two_track = QPushButton("🎧 Two-Track: OFF")
        self.btn_two_track.setCheckable(True)
        self.btn_two_track.setToolTip("Separate Local mic (Track 0) and Remote system audio (Track 1) to eliminate echo")
        self.btn_two_track.setStyleSheet(self._btn_style())
        self.btn_two_track.clicked.connect(self._toggle_two_track)
        header_row.addWidget(self.btn_two_track)

        c_layout.addLayout(header_row)

        # Recording Status Bar
        status_bar = QHBoxLayout()
        self.badge_status = QLabel("⏹  IDLE")
        self.badge_status.setStyleSheet("""
            background-color: #1E293B;
            color: #94A3B8;
            font-size: 11px;
            font-weight: bold;
            padding: 5px 10px;
            border-radius: 6px;
            border: 1px solid #334155;
        """)
        status_bar.addWidget(self.badge_status)

        self.level_bar = QProgressBar()
        self.level_bar.setRange(0, 100)
        self.level_bar.setValue(0)
        self.level_bar.setTextVisible(False)
        self.level_bar.setFixedHeight(8)
        self.level_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #38BDF8;
                border-radius: 3px;
            }
        """)
        status_bar.addWidget(self.level_bar, stretch=1)

        self.lbl_clock = QLabel("00:00:00")
        self.lbl_clock.setStyleSheet("""
            background-color: #0F172A;
            color: #38BDF8;
            font-size: 14px;
            font-weight: bold;
            font-family: 'Consolas', monospace;
            padding: 5px 12px;
            border-radius: 6px;
            border: 1px solid #334155;
        """)
        status_bar.addWidget(self.lbl_clock)

        self.btn_catchup = QPushButton("⚡ Catch Up")
        self.btn_catchup.setToolTip("What Did I Miss? Instant live recap of the last 5 minutes")
        self.btn_catchup.setStyleSheet(self._btn_style())
        self.btn_catchup.clicked.connect(self._on_catchup_clicked)
        status_bar.addWidget(self.btn_catchup)

        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setEnabled(False)
        self.btn_pause.setStyleSheet(self._btn_style())
        self.btn_pause.clicked.connect(self._toggle_pause)
        status_bar.addWidget(self.btn_pause)

        self.btn_record = QPushButton("🔴 Start Meeting Recording")
        self.btn_record.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                padding: 7px 16px;
                border-radius: 6px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
        """)
        self.btn_record.clicked.connect(self._toggle_recording)
        status_bar.addWidget(self.btn_record)

        c_layout.addLayout(status_bar)

        # Transcript Area
        lbl_live = QLabel("LIVE STREAMING TRANSCRIPT")
        lbl_live.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748B;")
        c_layout.addWidget(lbl_live)

        self.transcript_edit = QTextEdit()
        self.transcript_edit.setPlaceholderText(
            "Speech will stream here in real-time with automatic [HH:MM:SS] timestamps...\n"
            "Press 'Start Meeting Recording' and speak freely into your microphone."
        )
        self.transcript_edit.setStyleSheet("""
            QTextEdit {
                background-color: #0B0F19;
                color: #F8FAFC;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 14px;
                font-family: 'Consolas', monospace;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        c_layout.addWidget(self.transcript_edit, stretch=1)

        # Transcript search bar
        t_search_row = QHBoxLayout()
        self.txt_search_transcript = QLineEdit()
        self.txt_search_transcript.setPlaceholderText("Filter in transcript...")
        self.txt_search_transcript.setStyleSheet(self._input_style())
        self.txt_search_transcript.textChanged.connect(self._filter_transcript)
        t_search_row.addWidget(self.txt_search_transcript)
        c_layout.addLayout(t_search_row)


        # -------------------------------------------------------------
        # Right Studio: Smart Summary, Action Items & Minutes
        # -------------------------------------------------------------
        right_box = QWidget()
        r_layout = QVBoxLayout(right_box)
        r_layout.setContentsMargins(8, 0, 0, 0)
        r_layout.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #1E293B;
                background-color: #0B0F19;
                border-radius: 8px;
                padding: 8px;
            }
            QTabBar::tab {
                background-color: #1E293B;
                color: #94A3B8;
                padding: 7px 14px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background-color: #0284C7;
                color: #FFFFFF;
            }
        """)

        # Tab 1: Executive Summary & Decisions
        tab_summary = QWidget()
        ts_layout = QVBoxLayout(tab_summary)
        ts_layout.setContentsMargins(6, 6, 6, 6)
        self.summary_edit = QTextEdit()
        self.summary_edit.setPlaceholderText("Executive summary and key decisions will be generated here upon stopping the meeting...")
        self.summary_edit.setStyleSheet(self._doc_style())
        ts_layout.addWidget(self.summary_edit)
        self.tabs.addTab(tab_summary, "📌 Summary & Decisions")

        # Tab 2: Interactive Action Items Checklist
        tab_actions = QWidget()
        ta_layout = QVBoxLayout(tab_actions)
        ta_layout.setContentsMargins(6, 6, 6, 6)

        self.action_container = QWidget()
        self.action_layout = QVBoxLayout(self.action_container)
        self.action_layout.setContentsMargins(4, 4, 4, 4)
        self.action_layout.setSpacing(8)
        self.action_layout.addStretch()

        self.action_scroll = QTextEdit()
        self.action_scroll.setPlaceholderText("Action items detected during the meeting will appear here with interactive checkboxes...")
        self.action_scroll.setStyleSheet(self._doc_style())
        ta_layout.addWidget(self.action_scroll)

        # Quick Add Action Item
        add_box = QHBoxLayout()
        self.txt_new_action = QLineEdit()
        self.txt_new_action.setPlaceholderText("Add custom action item...")
        self.txt_new_action.setStyleSheet(self._input_style())
        self.txt_new_action.returnPressed.connect(self._add_custom_action)
        add_box.addWidget(self.txt_new_action)

        btn_add_act = QPushButton("Add")
        btn_add_act.setStyleSheet(self._btn_style())
        btn_add_act.clicked.connect(self._add_custom_action)
        add_box.addWidget(btn_add_act)
        ta_layout.addLayout(add_box)

        self.tabs.addTab(tab_actions, "✅ Action Items")

        # Tab 3: Meeting Minutes Scratchpad
        tab_notes = QWidget()
        tn_layout = QVBoxLayout(tab_notes)
        tn_layout.setContentsMargins(6, 6, 6, 6)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Type manual notes, attendees, links, or agenda items here during the meeting...")
        self.notes_edit.setStyleSheet(self._doc_style())
        tn_layout.addWidget(self.notes_edit)
        self.tabs.addTab(tab_notes, "📝 Minutes & Notes")

        # Tab 4: Guided Deliberation & Intelligence
        tab_deliberation = QWidget()
        td_layout = QVBoxLayout(tab_deliberation)
        td_layout.setContentsMargins(6, 6, 6, 6)
        td_layout.setSpacing(8)

        self.deliberation_edit = QTextEdit()
        self.deliberation_edit.setPlaceholderText(
            "Decision Weighing Matrix, Pros/Cons, and Risk Radar will appear here automatically...\n"
            "Powered by Sovereign Meeting Deliberation Engine."
        )
        self.deliberation_edit.setStyleSheet(self._doc_style())
        td_layout.addWidget(self.deliberation_edit, stretch=1)

        delib_btn_bar = QHBoxLayout()
        self.btn_copy_email = QPushButton("📧 Copy Email Draft")
        self.btn_copy_email.setStyleSheet(self._btn_style())
        self.btn_copy_email.clicked.connect(self._copy_followup_email)
        delib_btn_bar.addWidget(self.btn_copy_email)

        self.btn_copy_cards = QPushButton("🎫 Copy Task Cards")
        self.btn_copy_cards.setStyleSheet(self._btn_style())
        self.btn_copy_cards.clicked.connect(self._copy_task_cards)
        delib_btn_bar.addWidget(self.btn_copy_cards)

        self.btn_retention = QPushButton("🧹 Retention Policy & Purge")
        self.btn_retention.setStyleSheet(self._btn_style())
        self.btn_retention.clicked.connect(self._on_retention_clicked)
        delib_btn_bar.addWidget(self.btn_retention)

        td_layout.addLayout(delib_btn_bar)
        self.tabs.addTab(tab_deliberation, "⚖️ Deliberation")

        r_layout.addWidget(self.tabs, stretch=1)

        # Footer Actions
        btn_bar = QHBoxLayout()
        btn_copy_all = QPushButton("📋 Copy Full Report")
        btn_copy_all.setStyleSheet(self._btn_style())
        btn_copy_all.clicked.connect(self._copy_full_report)
        btn_bar.addWidget(btn_copy_all)

        btn_copy_acts = QPushButton("✅ Copy Actions")
        btn_copy_acts.setStyleSheet(self._btn_style())
        btn_copy_acts.clicked.connect(self._copy_action_items)
        btn_bar.addWidget(btn_copy_acts)

        btn_export = QPushButton("💾 Export Report...")
        btn_export.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-weight: 600;
                padding: 7px 14px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        btn_export.clicked.connect(self._export_report)
        btn_bar.addWidget(btn_export)

        r_layout.addLayout(btn_bar)
        self.workspace_tabs.addTab(sidebar, "Library")
        self.workspace_tabs.addTab(center_box, "Live transcript")
        self.workspace_tabs.addTab(right_box, "Notes & actions")
        self.workspace_tabs.setCurrentIndex(1)
        main_layout.addWidget(self.workspace_tabs)

    # -------------------------------------------------------------
    # Styles
    # -------------------------------------------------------------
    def _btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                font-weight: 600;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #334155;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #38BDF8;
            }
        """

    def _input_style(self) -> str:
        return """
            QLineEdit {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #38BDF8;
            }
        """

    def _doc_style(self) -> str:
        return """
            QTextEdit {
                background-color: #0B0F19;
                color: #F8FAFC;
                border: none;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 13px;
                line-height: 1.6;
            }
        """

    # -------------------------------------------------------------
    # Live Recording & Timer Controls
    # -------------------------------------------------------------
    def _toggle_recording(self):
        if not self.engine.is_recording:
            # Start
            title = self.txt_title.text().strip() or "Untitled Meeting"
            tpl = self.combo_template.currentData()
            sess = self.engine.start_meeting(title=title, template=tpl)
            self._current_meeting_id = sess.meeting_id

            self._elapsed_seconds = 0
            self.lbl_clock.setText("00:00:00")
            self._clock_timer.start(1000)

            self.badge_status.setText("●  RECORDING LIVE")
            self.badge_status.setStyleSheet("""
                background-color: #7F1D1D;
                color: #FCA5A5;
                font-size: 11px;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 6px;
                border: 1px solid #EF4444;
            """)
            self.btn_record.setText("⏹ Stop & Summarize")
            self.btn_record.setStyleSheet("""
                QPushButton {
                    background-color: #0284C7;
                    color: #FFFFFF;
                    font-weight: bold;
                    padding: 7px 16px;
                    border-radius: 6px;
                    border: none;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #0369A1;
                }
            """)
            self.btn_pause.setEnabled(True)
            self.btn_pause.setText("⏸ Pause")
            self.transcript_edit.clear()
        else:
            # Stop & Summarize
            self._clock_timer.stop()
            summary = self.engine.stop_meeting()

            self.badge_status.setText("⏹  IDLE")
            self.badge_status.setStyleSheet("""
                background-color: #1E293B;
                color: #94A3B8;
                font-size: 11px;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 6px;
                border: 1px solid #334155;
            """)
            self.btn_record.setText("🔴 Start Meeting Recording")
            self.btn_record.setStyleSheet("""
                QPushButton {
                    background-color: #DC2626;
                    color: #FFFFFF;
                    font-weight: bold;
                    padding: 7px 16px;
                    border-radius: 6px;
                    border: none;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #B91C1C;
                }
            """)
            self.btn_pause.setEnabled(False)
            self.level_bar.setValue(0)

            if summary:
                data_dict = summary.summary if (hasattr(summary, "summary") and summary.summary) else summary
                self._render_meeting_data(data_dict)
                self._reload_meeting_list()

                # Sovereign meeting insights recording
                try:
                    from engine.insights_engine import InsightsEngine
                    ins = InsightsEngine()
                    mins = max(1, self._elapsed_seconds // 60)
                    act_count = len(data_dict.get("action_items", [])) if hasattr(data_dict, "get") else 0
                    dec_count = len(data_dict.get("decisions", [])) if hasattr(data_dict, "get") else 0
                    ins.record_meeting(duration_minutes=mins, action_items_count=act_count, decisions_count=dec_count)
                except Exception:
                    pass

    def _toggle_pause(self):
        if not self.engine.is_recording:
            return
        if not self.engine.is_paused:
            self.engine.pause_meeting()
            self._clock_timer.stop()
            self.btn_pause.setText("▶ Resume")
            self.badge_status.setText("⏸  PAUSED")
            self.badge_status.setStyleSheet("""
                background-color: #78350F;
                color: #FDE68A;
                font-size: 11px;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 6px;
                border: 1px solid #F59E0B;
            """)
        else:
            self.engine.resume_meeting()
            self._clock_timer.start(1000)
            self.btn_pause.setText("⏸ Pause")
            self.badge_status.setText("●  RECORDING LIVE")
            self.badge_status.setStyleSheet("""
                background-color: #7F1D1D;
                color: #FCA5A5;
                font-size: 11px;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 6px;
                border: 1px solid #EF4444;
            """)

    def _on_clock_tick(self):
        self._elapsed_seconds += 1
        mins, s = divmod(self._elapsed_seconds, 60)
        hrs, m = divmod(mins, 60)
        self.lbl_clock.setText(f"{hrs:02d}:{m:02d}:{s:02d}")

    def _handle_live_segment_gui(self, seg: dict):
        spk = seg.get("speaker")
        spk_str = f"[{spk}] " if spk else ""
        line = f"[{seg.get('time', '00:00')}] {spk_str}{seg.get('text', '')}\n"
        self.transcript_edit.append(line.strip())

    def _handle_audio_level_gui(self, level: float):
        self.level_bar.setValue(min(100, int(level * 100)))

    def _on_audio_level(self, level: float):
        self._bridge.audio_level_received.emit(level)

    def _on_live_segment(self, seg: dict):
        self._bridge.segment_received.emit(seg)

    def append_segment(self, text: str):
        seg = self.engine.add_transcript_segment(text)
        if seg:
            payload = seg.to_dict() if hasattr(seg, "to_dict") else seg
            self._handle_live_segment_gui(payload)


    def _filter_transcript(self, query: str):
        q = query.strip().lower()
        if not q:
            return
        # Move cursor to find query in transcript
        doc = self.transcript_edit.document()
        cursor = doc.find(q)
        if not cursor.isNull():
            self.transcript_edit.setTextCursor(cursor)

    # -------------------------------------------------------------
    # Meeting Library & Sidebar
    # -------------------------------------------------------------
    def _reload_meeting_list(self):
        self.meeting_list.clear()
        meetings = self.engine.list_saved_meetings()
        for m in meetings:
            item = QListWidgetItem()
            title = m.get("title", "Untitled")
            date = m.get("date", "")
            dur = m.get("duration", "00:00")
            acts = m.get("action_items_count", 0)

            item.setText(f"🎙 {title}\n{date} • {dur} • {acts} tasks")
            item.setData(Qt.UserRole, m["meeting_id"])
            self.meeting_list.addItem(item)

    def _filter_meeting_list(self, query: str):
        q = query.strip().lower()
        for i in range(self.meeting_list.count()):
            item = self.meeting_list.item(i)
            match = (q in item.text().lower())
            item.setHidden(not match)

    def _on_meeting_selected(self, item: QListWidgetItem):
        meeting_id = item.data(Qt.UserRole)
        if not meeting_id:
            return
        data = self.engine.load_meeting(meeting_id)
        if data:
            self._current_meeting_id = meeting_id
            self._render_meeting_data(data)
            self.workspace_tabs.setCurrentIndex(2)

    def _on_new_meeting_clicked(self):
        if self.engine.is_recording:
            QMessageBox.warning(self, "Recording in Progress", "Please stop the current meeting before starting a new one.")
            return
        self._current_meeting_id = None
        self.txt_title.setText("New Team Discussion")
        self.lbl_clock.setText("00:00:00")
        self.transcript_edit.clear()
        self.summary_edit.clear()
        self.action_scroll.clear()
        self.notes_edit.clear()
        self.deliberation_edit.clear()
        self._last_deliberation_data = None
        self.workspace_tabs.setCurrentIndex(1)

    def _show_meeting_context_menu(self, pos):
        item = self.meeting_list.itemAt(pos)
        if not item:
            return
        meeting_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #38BDF8;
                color: #0F172A;
            }
        """)

        act_rename = menu.addAction("✏️ Rename Meeting...")
        act_delete = menu.addAction("🗑️ Delete Meeting")

        action = menu.exec(self.meeting_list.mapToGlobal(pos))
        if action == act_rename:
            new_title, ok = QInputDialog.getText(self, "Rename Meeting", "Enter new meeting title:")
            if ok and new_title.strip():
                self.engine.update_meeting(meeting_id, {"title": new_title.strip()})
                self._reload_meeting_list()
        elif action == act_delete:
            confirm = QMessageBox.question(
                self, "Delete Meeting", "Are you sure you want to delete this meeting session?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                self.engine.delete_meeting(meeting_id)
                self._reload_meeting_list()

    # -------------------------------------------------------------
    # Data Rendering & Intelligence
    # -------------------------------------------------------------
    def _render_meeting_data(self, data: Dict[str, Any]):
        self.txt_title.setText(data.get("title", "Untitled Meeting"))

        # Set Template
        tpl = data.get("template", "general")
        idx = self.combo_template.findData(tpl)
        if idx >= 0:
            self.combo_template.setCurrentIndex(idx)

        # Set Transcript
        self.transcript_edit.setPlainText(data.get("transcript", ""))

        # Set Summary
        lines = []
        lines.append(f"# {data.get('title', 'Meeting Notes')}")
        lines.append(f"**Date:** {data.get('date', '')} | **Duration:** {data.get('duration', '00:00')} | **Words:** {data.get('total_words', 0)}\n")

        lines.append("## 📌 Key Decisions")
        decisions = data.get("decisions", [])
        if decisions:
            for d in decisions:
                lines.append(f"- **Decision:** {d}")
        else:
            lines.append("- *(No formal decisions explicitly declared)*")
        lines.append("")

        lines.append("## 💡 Discussion Highlights")
        key_pts = data.get("key_points", [])
        if key_pts:
            for pt in key_pts:
                lines.append(f"- {pt}")
        else:
            lines.append("- Discussion captured in the full transcript.")

        self.summary_edit.setPlainText("\n".join(lines))

        # Set Action Items
        act_lines = []
        for a in data.get("action_items", []):
            if isinstance(a, dict):
                chk = "x" if a.get("done") else " "
                act_lines.append(f"- [{chk}] {a.get('text', '')}")
            else:
                chk = "x" if getattr(a, "done", False) else " "
                txt = getattr(a, "text", str(a))
                act_lines.append(f"- [{chk}] {txt}")
        self.action_scroll.setPlainText("\n".join(act_lines))


        # Set Notes
        self.notes_edit.setPlainText(data.get("notes", ""))

        # Populate Deliberation & Intelligence
        self._populate_deliberation_ui(data)

    def _add_custom_action(self):
        text = self.txt_new_action.text().strip()
        if not text:
            return
        curr = self.action_scroll.toPlainText().strip()
        new_text = (curr + f"\n- [ ] {text}").strip()
        self.action_scroll.setPlainText(new_text)
        self.txt_new_action.clear()

        # Update saved meeting if loaded
        if self._current_meeting_id:
            data = self.engine.load_meeting(self._current_meeting_id)
            if data:
                acts = data.get("action_items", [])
                acts.append({"id": f"act_{len(acts)+1}", "text": text, "done": False})
                self.engine.update_meeting(self._current_meeting_id, {"action_items": acts})

    # -------------------------------------------------------------
    # Exports & Copying
    # -------------------------------------------------------------
    def _copy_full_report(self):
        report = self.engine.format_markdown_report({
            "title": self.txt_title.text().strip(),
            "template": self.combo_template.currentData(),
            "date": self.lbl_clock.text(),
            "duration": self.lbl_clock.text(),
            "transcript": self.transcript_edit.toPlainText(),
            "decisions": _parse_decision_lines(self.summary_edit.toPlainText()),
            "key_points": [line[2:] for line in self.summary_edit.toPlainText().split("\n") if line.startswith("- ") and not line.startswith("- **Decision:")],
            "action_items": [{"text": line[6:], "done": line.startswith("- [x]")} for line in self.action_scroll.toPlainText().split("\n") if line.startswith("- [")],
            "notes": self.notes_edit.toPlainText()
        })
        pyperclip.copy(report)
        QMessageBox.information(self, "Copied", "Full meeting report copied to clipboard in Markdown format!")

    def _copy_action_items(self):
        text = self.action_scroll.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Action Items", "No action items to copy.")
            return
        pyperclip.copy(text)
        QMessageBox.information(self, "Copied", "Action items checklist copied to clipboard!")

    def _export_report(self):
        report = self.engine.format_markdown_report({
            "title": self.txt_title.text().strip(),
            "template": self.combo_template.currentData(),
            "date": self.lbl_clock.text(),
            "duration": self.lbl_clock.text(),
            "transcript": self.transcript_edit.toPlainText(),
            "decisions": _parse_decision_lines(self.summary_edit.toPlainText()),
            "key_points": [line[2:] for line in self.summary_edit.toPlainText().split("\n") if line.startswith("- ") and not line.startswith("- **Decision:")],
            "action_items": [{"text": line[6:], "done": line.startswith("- [x]")} for line in self.action_scroll.toPlainText().split("\n") if line.startswith("- [")],
            "notes": self.notes_edit.toPlainText()
        })

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Meeting Report", str(Path.home() / "meeting_notes.md"),
            "Markdown (*.md);;Text (*.txt);;JSON (*.json)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(report)
                QMessageBox.information(self, "Export Complete", f"Saved meeting notes to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Could not write file: {e}")

    # -------------------------------------------------------------
    # Deliberation, Translation & Catch-Up Intelligence
    # -------------------------------------------------------------
    def _toggle_translation(self):
        enabled = self.btn_translate.isChecked()
        self.engine.set_translation_mode(enabled, "en")
        if enabled:
            self.btn_translate.setText("🌐 Translate: EN")
            self.btn_translate.setStyleSheet("""
                QPushButton {
                    background-color: #0369A1;
                    color: #FFFFFF;
                    font-weight: 600;
                    padding: 6px 12px;
                    border-radius: 6px;
                    border: 1px solid #38BDF8;
                    font-size: 12px;
                }
            """)
        else:
            self.btn_translate.setText("🌐 Translate: OFF")
            self.btn_translate.setStyleSheet(self._btn_style())

    def _toggle_two_track(self):
        enabled = self.btn_two_track.isChecked()
        self.engine.enable_two_track(enabled)
        if enabled:
            self.btn_two_track.setText("🎧 Two-Track: ON")
            self.btn_two_track.setStyleSheet("""
                QPushButton {
                    background-color: #0369A1;
                    color: #FFFFFF;
                    font-weight: 600;
                    padding: 6px 12px;
                    border-radius: 6px;
                    border: 1px solid #38BDF8;
                    font-size: 12px;
                }
            """)
        else:
            self.btn_two_track.setText("🎧 Two-Track: OFF")
            self.btn_two_track.setStyleSheet(self._btn_style())

    def _on_catchup_clicked(self):
        recap = self.engine.get_live_catchup(window_minutes=5)
        msg_lines = [
            f"⚡ What Did I Miss? (Last {recap.window_minutes} mins)",
            f"Active Speakers: {recap.active_speakers_count} | Key Points: {recap.bullet_count}\n"
        ]
        if recap.summary_points:
            for pt in recap.summary_points:
                msg_lines.append(f"• {pt}")
        else:
            msg_lines.append("• No recent speech detected in the catch-up window.")

        if recap.immediate_action_items:
            msg_lines.append("\nImmediate Action Items:")
            for act in recap.immediate_action_items:
                msg_lines.append(f"⚡ {act}")

        recap_text = "\n".join(msg_lines)
        QMessageBox.information(self, "⚡ Live Catch-Up Recap", recap_text)

    def _populate_deliberation_ui(self, data: Optional[Dict[str, Any]] = None):
        if not data:
            self.deliberation_edit.clear()
            return
        self._last_deliberation_data = data

        topics = self.engine.deliberation.weigh_decisions(data)
        risks = self.engine.deliberation.detect_risks_and_blockers(data)

        lines = []
        lines.append(f"# ⚖️ Deliberation & Intelligence: {data.get('title', 'Meeting Notes')}\n")

        lines.append("## 📊 Decision Weighing Matrix")
        if topics:
            for t in topics:
                status_emoji = "✅" if t.status == "decided" else "💬"
                lines.append(f"### {status_emoji} {t.title} [{t.status.upper()}]")
                if t.pros:
                    lines.append("  **Pros / Benefits:**")
                    for pro in t.pros:
                        lines.append(f"    + {pro}")
                if t.cons:
                    lines.append("  **Cons / Risks:**")
                    for con in t.cons:
                        lines.append(f"    - {con}")
                if t.consensus:
                    lines.append(f"  **Consensus:** {t.consensus}")
                lines.append("")
        else:
            lines.append("*(No trade-offs or contested decisions extracted from session)*\n")

        lines.append("## 🚨 Risk & Blocker Radar")
        if risks:
            for r in risks:
                sev_badge = f"[{r.severity.value}]"
                lines.append(f"- **{sev_badge}** {r.description}")
                if r.mitigation_hint:
                    lines.append(f"  ↳ *Mitigation:* {r.mitigation_hint}")
        else:
            lines.append("- *(Zero high/medium blockers detected)*")

        self.deliberation_edit.setPlainText("\n".join(lines))

    def _copy_followup_email(self):
        data = getattr(self, "_last_deliberation_data", None)
        if not data and self._current_meeting_id:
            data = self.engine.load_meeting(self._current_meeting_id)
        if not data:
            data = {
                "title": self.txt_title.text().strip(),
                "duration": self.lbl_clock.text(),
                "transcript": self.transcript_edit.toPlainText(),
                "decisions": _parse_decision_lines(self.summary_edit.toPlainText()),
                "action_items": [{"text": line[6:], "done": line.startswith("- [x]")} for line in self.action_scroll.toPlainText().split("\n") if line.startswith("- [")],
            }
        draft = self.engine.deliberation.draft_followup_email(data)
        pyperclip.copy(draft)
        QMessageBox.information(self, "Follow-Up Email Copied", "Executive follow-up email draft copied to clipboard!")

    def _copy_task_cards(self):
        data = getattr(self, "_last_deliberation_data", None)
        if not data and self._current_meeting_id:
            data = self.engine.load_meeting(self._current_meeting_id)
        if not data:
            data = {
                "title": self.txt_title.text().strip(),
                "action_items": [{"text": line[6:], "done": line.startswith("- [x]")} for line in self.action_scroll.toPlainText().split("\n") if line.startswith("- [")],
            }
        cards = self.engine.deliberation.generate_task_cards(data)
        card_text = "\n\n---\n\n".join(c.to_markdown() for c in cards)
        if not card_text:
            card_text = "No action items available to convert to task cards."
        pyperclip.copy(card_text)
        QMessageBox.information(self, "Task Cards Copied", f"Generated and copied {len(cards)} Markdown task cards to clipboard!")

    def _on_retention_clicked(self):
        policy = self.engine.deliberation.retention_policy
        items = ["7 days (Ephemeral)", "30 days (Standard Sprint)", "90 days (Quarterly)", "365 days (Annual)", "Keep Indefinitely (0 days)"]
        choice, ok = QInputDialog.getItem(self, "Retention Policy", "Set retention policy and purge sessions older than:", items, 1, False)
        if ok and choice:
            days = int(choice.split(" ")[0]) if not choice.startswith("Keep") else 0
            policy.max_age_days = days
            try:
                from engine.config import load_config, save_config
                cfg = load_config()
                cfg["meeting_retention_days"] = days
                save_config(cfg)
            except Exception:
                pass
            deleted = self.engine.deliberation.enforce_retention_policy()
            self._reload_meeting_list()
            QMessageBox.information(self, "Retention Policy Saved", f"Retention policy set to {days} days and persisted.\nPurged {deleted} expired meeting session(s).")
