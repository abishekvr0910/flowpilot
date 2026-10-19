"""
FlowPilot Local Productivity Insights View
Displays lifetime words, WPM velocity, daily streaks, and hours saved.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFrame
)
from PySide6.QtCore import Qt

from engine.insights_engine import get_insights_engine, InsightsEngine

class InsightsView(QWidget):
    def __init__(self, parent=None, engine: Optional[InsightsEngine] = None):
        super().__init__(parent)
        self.engine = engine or get_insights_engine()
        self._init_ui()
        self.refresh_metrics()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("Productivity Insights")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #F8FAFC;")
        lbl_sub = QLabel("100% offline, private dictation velocity and retention analytics.")
        lbl_sub.setStyleSheet("font-size: 13px; color: #94A3B8;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)
        header.addStretch()

        btn_refresh = QPushButton("↻ Refresh")
        btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #38BDF8;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 6px;
                border: 1px solid #334155;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        btn_refresh.clicked.connect(self.refresh_metrics)
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        # 4 Hero Metric Cards in a Grid
        cards_grid = QGridLayout()
        cards_grid.setSpacing(14)

        self.card_words, self.val_words = self._make_metric_card("Total Words", "0", "words dictated lifetime", "#38BDF8")
        self.card_wpm, self.val_wpm = self._make_metric_card("Dictation Speed", "150", "average words per minute", "#34D399")
        self.card_streak, self.val_streak = self._make_metric_card("Active Streak", "1", "consecutive active days", "#FBBF24")
        self.card_time, self.val_time = self._make_metric_card("Time Saved", "0.0h", "hours saved vs. typing", "#A78BFA")

        # Row 2: Meeting & Guided Deliberation Intelligence
        self.card_meetings, self.val_meetings = self._make_metric_card("Meeting Hours", "0.0h", "total hours in calls/meetings", "#F43F5E")
        self.card_decisions, self.val_decisions = self._make_metric_card("Decisions Reached", "0", "consensus decisions recorded", "#10B981")
        self.card_actions, self.val_actions = self._make_metric_card("Action Items", "0", "commitments tracked", "#06B6D4")
        self.card_deep_work, self.val_deep_work = self._make_metric_card("Deep Work Ratio", "100%", "dictation vs meeting load", "#E879F9")

        cards_grid.addWidget(self.card_words, 0, 0)
        cards_grid.addWidget(self.card_wpm, 0, 1)
        cards_grid.addWidget(self.card_streak, 0, 2)
        cards_grid.addWidget(self.card_time, 0, 3)

        cards_grid.addWidget(self.card_meetings, 1, 0)
        cards_grid.addWidget(self.card_decisions, 1, 1)
        cards_grid.addWidget(self.card_actions, 1, 2)
        cards_grid.addWidget(self.card_deep_work, 1, 3)
        layout.addLayout(cards_grid)

        # Freedom Banner (Counter to Wispr Flow's 0-words limit)
        banner = QFrame()
        banner.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #0284C7;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        b_layout = QHBoxLayout(banner)
        b_icon = QLabel("⚡")
        b_icon.setStyleSheet("font-size: 24px;")
        b_layout.addWidget(b_icon)

        b_text_box = QVBoxLayout()
        b_title = QLabel("Unlimited Words & Zero Cloud Limits")
        b_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #F8FAFC;")
        b_desc = QLabel("FlowPilot runs 100% offline via local Faster-Whisper. You will never see a '0 words left' limit or subscription paywall.")
        b_desc.setStyleSheet("font-size: 12px; color: #94A3B8;")
        b_text_box.addWidget(b_title)
        b_text_box.addWidget(b_desc)
        b_layout.addLayout(b_text_box)
        b_layout.addStretch()
        layout.addWidget(banner)

        # Recent Session Activity Table
        lbl_table = QLabel("Recent Dictation Sessions")
        lbl_table.setStyleSheet("font-size: 14px; font-weight: bold; color: #F8FAFC;")
        layout.addWidget(lbl_table)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Target App", "Words", "Duration", "Speed"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
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
                font-weight: bold;
                padding: 6px;
                border: 1px solid #334155;
            }
        """)
        layout.addWidget(self.table)

    def _make_metric_card(self, title: str, default_val: str, caption: str, accent_color: str):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 14px;
            }}
        """)
        vbox = QVBoxLayout(card)
        vbox.setSpacing(4)

        lbl_t = QLabel(title.upper())
        lbl_t.setStyleSheet("font-size: 11px; font-weight: bold; color: #94A3B8; letter-spacing: 0.5px;")
        vbox.addWidget(lbl_t)

        lbl_v = QLabel(default_val)
        lbl_v.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {accent_color};")
        vbox.addWidget(lbl_v)

        lbl_c = QLabel(caption)
        lbl_c.setStyleSheet("font-size: 11px; color: #64748B;")
        vbox.addWidget(lbl_c)

        return card, lbl_v

    def refresh_metrics(self):
        m = self.engine.get_metrics()
        self.val_words.setText(m.get("total_words_formatted", "0"))
        self.val_wpm.setText(f"{m.get('wpm', 150)} wpm")
        self.val_streak.setText(f"{m.get('streak', 1)} days")
        self.val_time.setText(f"{m.get('time_saved_hours', 0.0)}h")

        # Meeting Intelligence metrics
        m_hrs = m.get("meeting_hours", 0.0)
        self.val_meetings.setText(f"{m_hrs}h")
        self.val_decisions.setText(str(m.get("meeting_decisions", 0)))
        self.val_actions.setText(str(m.get("meeting_actions_created", 0)))

        # Deep work calculation: dictation hours vs meeting hours
        dict_hrs = m.get("time_saved_hours", 0.0) * 1.5
        total_hrs = dict_hrs + m_hrs
        deep_pct = 100 if m_hrs == 0 else int(max(10, min(100, (dict_hrs / (total_hrs or 1.0)) * 100)))
        self.val_deep_work.setText(f"{deep_pct}%")

        # Populate table
        recent = m.get("recent_sessions", [])
        self.table.setRowCount(0)
        for row, sess in enumerate(reversed(recent[-25:])):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(sess.get("timestamp", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(str(sess.get("app", "Desktop"))))
            self.table.setItem(row, 2, QTableWidgetItem(f"{sess.get('words', 0)} words"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{sess.get('duration', 0.0)}s"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{sess.get('wpm', 0.0)} wpm"))
