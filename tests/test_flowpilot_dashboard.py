"""
Tests for FlowPilot Master Desktop Dashboard Window
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

from ui.flowpilot_dashboard import FlowPilotDashboard
from engine.companion_store import get_companion_store

app = QApplication.instance() or QApplication(sys.argv)

class TestFlowPilotDashboard(unittest.TestCase):
    def setUp(self):
        self.dash = FlowPilotDashboard(config={})

    def tearDown(self):
        self.dash.close()

    def test_dashboard_initialization(self):
        self.assertIsNotNone(self.dash.scratchpad_view)
        self.assertIsNotNone(self.dash.notetaker_view)
        self.assertIsNotNone(self.dash.insights_view)
        self.assertIsNotNone(self.dash.transforms_view)
        self.assertIsNotNone(self.dash.history_view)
        self.assertEqual(self.dash.stack.count(), 8)


    def test_companion_quick_switch(self):
        received_companion = []
        self.dash.companion_changed.connect(lambda pid: received_companion.append(pid))

        self.dash._select_companion("kitty")
        self.assertIn("kitty", received_companion)
        self.assertEqual(self.dash.store.get("selected_asset_id"), "kitty")

        self.dash._select_companion("dog")
        self.assertIn("dog", received_companion)
        self.assertEqual(self.dash.store.get("selected_asset_id"), "dog")

    def test_scratchpad_insert_and_count(self):
        sp = self.dash.scratchpad_view
        sp.editor.clear()
        sp.insert_text("This is an in-app voice draft test.")
        self.assertEqual(sp.editor.toPlainText().strip(), "This is an in-app voice draft test.")
        words = len(sp.editor.toPlainText().split())
        self.assertEqual(words, 7)

    def test_notetaker_append(self):
        nv = self.dash.notetaker_view
        nv.engine.start_meeting("Test Session")
        nv.append_segment("Hello from dashboard notetaker.")
        self.assertIn("Hello from dashboard notetaker.", nv.transcript_edit.toPlainText())

if __name__ == "__main__":
    unittest.main()
