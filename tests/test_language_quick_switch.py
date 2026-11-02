"""
Unit test for Language Quick-Switch (Tray Submenu, Hotkey Ctrl+Alt+L, and Dynamic Cycle).
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from ui.tray_manager import TrayManager


class TestLanguageQuickSwitch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_01_tray_menu_has_ta_and_pl_actions(self):
        """Verifies that Tamil and Polish are top-level options in the tray menu."""
        tray = TrayManager()
        self.assertIn("ta", tray.lang_actions)
        self.assertIn("pl", tray.lang_actions)
        self.assertIn("en", tray.lang_actions)
        self.assertIn("auto", tray.lang_actions)

        # Check action texts
        self.assertIn("Tamil", tray.lang_actions["ta"].text())
        self.assertIn("Polish", tray.lang_actions["pl"].text())

    def test_02_tray_quick_switch_action_and_signals(self):
        """Verifies that action_cycle_lang exists and signal is fired."""
        tray = TrayManager()
        self.assertTrue(hasattr(tray, "action_cycle_lang"))
        self.assertIn("Ctrl+Alt+L", tray.action_cycle_lang.text())

        fired = []
        tray.cycle_language_requested.connect(lambda: fired.append(True))
        tray.action_cycle_lang.trigger()
        self.assertEqual(len(fired), 1)

    def test_03_active_language_display_update(self):
        """Verifies that set_language_info updates the cycle action label."""
        tray = TrayManager()
        tray.set_language_info("ta")
        self.assertIn("Tamil", tray.action_cycle_lang.text())

        tray.set_language_info("en")
        self.assertIn("English", tray.action_cycle_lang.text())

        tray.set_language_info("pl")
        self.assertIn("Polish", tray.action_cycle_lang.text())

    def test_04_cycle_progression(self):
        """Verifies that cycling progresses through EN -> TA -> PL -> Auto."""
        from desktop_app import FlowPilotApp
        # Instantiate with headless mocks to prevent launching actual worker threads
        app = FlowPilotApp.__new__(FlowPilotApp)
        app.config = {"language": "en", "local_model_size": "base"}
        app.tray = TrayManager()
        app.orchestrator = type("MockOrchestrator", (), {"update_config": lambda *a: True})()

        # Step 1: en -> ta
        app.cycle_language_quick_switch()
        self.assertEqual(app.config["language"], "ta")

        # Step 2: ta -> pl
        app.cycle_language_quick_switch()
        self.assertEqual(app.config["language"], "pl")

        # Step 3: pl -> auto
        app.cycle_language_quick_switch()
        self.assertEqual(app.config["language"], "auto")

        # Step 4: auto -> en
        app.cycle_language_quick_switch()
        self.assertEqual(app.config["language"], "en")


if __name__ == "__main__":
    unittest.main()
