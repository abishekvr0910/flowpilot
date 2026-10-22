"""Render real Qt workspace screens without microphone, clipboard or user-profile access.

Usage: python scripts/preview_workspace.py --output scratch/workspace-preview
"""
import argparse
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "scratch/workspace-preview")
    parser.add_argument("--theme", choices=("sand", "obsidian"), default="sand")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    with tempfile.TemporaryDirectory(prefix="flowpilot-ui-preview-") as directory:
        profile = Path(directory)
        with patch.dict(os.environ, {"FLOWPILOT_CONFIG_DIR": directory, "FLOWPILOT_CONFIG_FILE": str(profile / "config.json")}), patch.object(Path, "home", return_value=profile):
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import QCoreApplication, QEvent
            from PySide6.QtGui import QFontDatabase, QFont
            from ui.flowpilot_dashboard import FlowPilotDashboard
            from engine.companion_store import get_companion_store
            app = QApplication.instance() or QApplication([])
            # Windows' offscreen Qt plugin needs explicit local font registration.
            for filename in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf"):
                font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / filename
                if font_path.exists():
                    QFontDatabase.addApplicationFont(str(font_path))
            app.setFont(QFont("Segoe UI", 10))
            get_companion_store().update({"selected_asset_id": "kiki", "reduced_motion": True, "cat_palette": "autumn"})
            with patch("sounddevice.query_devices", return_value=[]):
                dashboard = FlowPilotDashboard(config={"hotkey": "F9", "language": "en", "local_model_size": "base", "save_history_text": False, "ui_theme": args.theme}, on_dictate=lambda: None)
                dashboard.show()
                for name, page in (("home", 0), ("studio", 8), ("settings", 9),
                                   ("scratchpad", 3), ("meetings", 4)):
                    dashboard._on_nav_clicked(page)
                    for width, height, suffix in ((1160, 820, ""), (880, 580, "-compact")):
                        dashboard.resize(width, height)
                        for _ in range(5):
                            app.processEvents()
                        dest = args.output / f"{name}{suffix}.png"
                        if not dashboard.grab().save(str(dest)):
                            raise RuntimeError(f"Could not save {dest}")
                        print(f"Rendered {dest} ({dashboard.width()}x{dashboard.height()})")
                dashboard.scratchpad_view._autosave_timer.stop()
                dashboard.close()
                dashboard.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                app.processEvents()


if __name__ == "__main__":
    main()
