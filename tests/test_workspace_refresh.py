"""Hardware-free checks for the native workspace presentation and bindings."""
from pathlib import Path
from unittest.mock import patch
import sys
import os
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import QCoreApplication, QEvent, QPoint


@pytest.fixture
def dashboard(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOWPILOT_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("FLOWPILOT_CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from ui.flowpilot_dashboard import FlowPilotDashboard
    import ui.scratchpad_view as scratchpad
    import engine.personalization as personalization
    import engine.insights_engine as insights
    import engine.meeting_notetaker as meetings
    import engine.companion_store as comp_store
    old_comp_store = comp_store._store_instance
    comp_store._store_instance = comp_store.CompanionStore(storage_dir=tmp_path)
    monkeypatch.setattr(scratchpad, "AUTOSAVE_FILE", tmp_path / "scratchpad.txt")
    monkeypatch.setattr(personalization, "PERSONALIZATION_FILE", tmp_path / "personalization.json")
    monkeypatch.setattr(insights, "INSIGHTS_FILE", tmp_path / "insights.json")
    monkeypatch.setattr(meetings, "MEETINGS_DIR", tmp_path / "meetings")
    app = QApplication.instance() or QApplication([])
    with patch("sounddevice.query_devices", return_value=[]), \
         patch("sounddevice.InputStream", side_effect=AssertionError("UI must not open a microphone")), \
         patch("engine.stt_engine.STTEngine._get_local_model", side_effect=AssertionError("UI must not load a model")):
        window = FlowPilotDashboard(config={"hotkey": "F9", "language": "en", "local_model_size": "base", "save_history_text": False})
        window.show()
        app.processEvents()
        try:
            yield window
        finally:
            comp_store._store_instance = old_comp_store
        window.scratchpad_view._autosave_timer.stop()
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        app.processEvents()


def test_home_uses_configured_shortcut_and_no_false_readiness(dashboard):
    assert dashboard.home_page.shortcut_label.text() == "F9"
    assert "F9" in dashboard.home_page.btn_dictate.text()
    assert "Configured:" in dashboard.home_page.config_label.text()
    assert "history is off" in dashboard.home_page.retention_label.text()


def test_native_home_does_not_embed_competitor_renderer_or_read_credentials(dashboard):
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "package.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "flowpilot"
    assert not (root / "ui" / "wispr_bridge.py").exists()
    assert not (root / "ui" / "wispr_renderer").exists()
    assert getattr(dashboard.home_page, "web_view", None) is None
    home_source = (root / "ui" / "workspace_home.py").read_text(encoding="utf-8")
    assert "QWebEngine" not in home_source


def test_saved_settings_refresh_home_and_reject_failed_update(dashboard):
    dashboard.on_save_config = lambda config: False
    assert dashboard._on_save_settings({"hotkey": "F8"}) is False
    assert dashboard.config["hotkey"] == "F9"
    dashboard.on_save_config = lambda config: True
    assert dashboard._on_save_settings({"hotkey": "F8", "language": "ta", "local_model_size": "small"})
    assert dashboard.home_page.shortcut_label.text() == "F8"
    assert "Tamil" in dashboard.home_page.config_label.text()
    assert "small" in dashboard.home_page.config_label.text()


def test_studio_is_embedded_and_cancel_does_not_apply(dashboard):
    dashboard._on_nav_clicked(8)
    studio = dashboard.stack.currentWidget()
    assert studio.embedded and not studio.isWindow()
    old = studio.store.get("selected_asset_id")
    studio._draft["selected_asset_id"] = "nimbus"
    studio.reject()
    assert dashboard.stack.currentIndex() == 0
    assert studio.store.get("selected_asset_id") == old


def test_studio_apply_and_search_and_preview_states(dashboard):
    applied = []
    dashboard.companion_settings_applied.connect(applied.append)
    dashboard._on_nav_clicked(8)
    studio = dashboard.stack.currentWidget()
    studio.search_companions.setText("Kiki")
    visible = [button for button in studio.comp_btn_group.buttons() if not button.isHidden()]
    assert len(visible) == 1 and visible[0].property("comp_id") == "kiki"
    assert not visible[0].icon().isNull()
    visible[0].click()
    studio._draft["reduced_motion"] = True
    studio._draft["cat_palette"] = "frost"
    studio._on_apply_clicked()
    assert studio.store.get("selected_asset_id") == "kiki"
    assert dashboard.stack.currentIndex() == 8
    assert "Kiki" in dashboard.home_page.companion_label.text()
    assert applied[-1]["reduced_motion"] is True
    assert applied[-1]["cat_palette"] == "frost"
    studio.preview_state.setCurrentIndex(studio.preview_state.findData("unverified"))
    assert studio.preview_widget._preview_state == "unverified"


def test_settings_embedded_save_keeps_page_and_shared_personalization(dashboard):
    dashboard._on_nav_clicked(9)
    settings = dashboard.stack.currentWidget()
    assert settings.embedded and not settings.isWindow()
    assert settings.personalization is dashboard.personalization
    settings.combo_shortcut.setCurrentText("F8")
    with patch.object(settings, "_test_current_hotkey", return_value=True):
        settings._save_settings()
    assert dashboard.stack.currentIndex() == 9
    assert dashboard.home_page.shortcut_label.text() == "F8"
    assert "saved" in settings.save_status.text()


def test_preview_stops_when_hidden_and_reduced_motion(dashboard):
    preview = dashboard.home_page.preview
    preview.set_companion({"id": "kitty", "type": "builtin"}, reduced_motion=False)
    assert preview._anim_timer.isActive()
    dashboard._on_nav_clicked(2)
    assert not preview._anim_timer.isActive()
    dashboard._on_nav_clicked(0)
    preview.set_companion({"id": "kitty", "type": "builtin"}, reduced_motion=True)
    assert not preview._anim_timer.isActive()


def test_navigation_keeps_every_existing_tool_accessible(dashboard):
    for page in range(10):
        dashboard._on_nav_clicked(page)
        assert dashboard.stack.currentIndex() == page
        assert dashboard.nav_group.checkedId() == page


def test_compact_window_does_not_force_horizontal_growth(dashboard):
    for page in (0, 8, 9):
        dashboard._on_nav_clicked(page)
        dashboard.resize(880, 580)
        QApplication.processEvents()
        assert dashboard.width() == 880
        assert dashboard.height() == 580


def test_compact_settings_save_action_is_fully_visible(dashboard):
    dashboard._on_nav_clicked(9)
    dashboard.resize(880, 580)
    QApplication.processEvents()
    settings = dashboard.stack.currentWidget()
    save = next(button for button in settings.findChildren(QPushButton)
                if button.text() == "Save changes")
    assert save.mapTo(settings, QPoint(save.width(), 0)).x() <= settings.width()
    assert settings.mapTo(dashboard.stack, QPoint(settings.width(), 0)).x() <= dashboard.stack.width()
    assert save.mapTo(dashboard, QPoint(save.width(), 0)).x() <= dashboard.width()
    assert save.width() >= save.fontMetrics().horizontalAdvance(save.text()) + 24


def test_workspace_theme_is_saved_and_navigation_stays_visible(dashboard):
    assert "#f5f4f0" in dashboard.styleSheet().lower()
    dashboard._on_nav_clicked(9)
    settings = dashboard.stack.currentWidget()
    assert settings.combo_ui_theme.currentData() == "sand"
    settings.combo_ui_theme.setCurrentIndex(settings.combo_ui_theme.findData("obsidian"))
    with patch.object(settings, "_test_current_hotkey", return_value=True):
        settings._save_settings()
    assert dashboard.config["ui_theme"] == "obsidian"
    assert "#101715" in dashboard.styleSheet().lower()
    assert "#101715" in settings.styleSheet().lower()
    dashboard._on_nav_clicked(0)
    assert dashboard.sidebar_scroll.isVisible()
    dashboard._on_nav_clicked(8)
    assert "#101715" in dashboard.stack.currentWidget().styleSheet().lower()
    dashboard._on_nav_clicked(9)
    assert dashboard.stack.currentWidget().combo_ui_theme.currentData() == "obsidian"


def test_meeting_workspace_keeps_recording_controls_in_bounds(dashboard):
    dashboard._on_nav_clicked(4)
    dashboard.resize(880, 580)
    QApplication.processEvents()
    meetings = dashboard.notetaker_view
    assert [meetings.workspace_tabs.tabText(i) for i in range(3)] == [
        "Library", "Live transcript", "Notes & actions"]
    assert meetings.btn_record.isVisible()
    assert meetings.btn_record.mapTo(meetings, QPoint(meetings.btn_record.width(), 0)).x() <= meetings.width()
    assert dashboard.sidebar_scroll.isVisible()


def test_show_on_desktop_does_not_apply_draft(dashboard):
    requested = []
    dashboard.show_companion_requested.connect(lambda: requested.append(True))
    dashboard._on_nav_clicked(8)
    studio = dashboard.stack.currentWidget()
    old = studio.store.get("selected_asset_id")
    studio._draft["selected_asset_id"] = "nimbus"
    studio.btn_show_live.click()
    assert requested == [True]
    assert studio.store.get("selected_asset_id") == old


def test_recovery_controls_use_existing_handlers(dashboard):
    from engine.text_injector import TextInjector
    with patch.object(TextInjector, "last_injected_text", "A synthetic recovery fixture."):
        dashboard.home_page.refresh()
        assert dashboard.home_page.btn_copy.isEnabled()
        assert dashboard.home_page.btn_paste.isEnabled()
        with patch.object(TextInjector, "_safe_clipboard_copy", return_value=True) as copy_text, \
             patch("ui.flowpilot_dashboard.QMessageBox.information"):
            dashboard.home_page.btn_copy.click()
        copy_text.assert_called_once_with("A synthetic recovery fixture.")


def _wheel(dashboard, combo, delta=120):
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtCore import QPointF, QPoint, Qt
    center = QPointF(combo.rect().center())
    event = QWheelEvent(
        center, QPointF(combo.mapToGlobal(center.toPoint())),
        QPoint(0, 0), QPoint(0, delta),
        Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False
    )
    QApplication.sendEvent(combo, event)
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    QApplication.processEvents()
    return event


def test_wheel_over_closed_combo_never_changes_value_and_scrolls_page(dashboard):
    combo = dashboard.home_page.visibility_choice
    assert combo.count() >= 2
    combo.blockSignals(True)
    combo.setCurrentIndex(0)
    combo.blockSignals(False)
    before = combo.currentIndex()
    mode_requests = []
    dashboard.companion_visibility_requested.connect(mode_requests.append)
    _wheel(dashboard, combo, delta=240)
    assert combo.currentIndex() == before
    assert mode_requests == []


def test_wheel_over_closed_combo_forwards_to_parent_scroll_area(dashboard):
    from PySide6.QtWidgets import QAbstractScrollArea
    combo = dashboard.home_page.visibility_choice
    # At the minimum window size the home page does not fit and must remain
    # reachable by wheel scrolling even over the combo.
    dashboard.resize(880, 580)
    QApplication.processEvents()
    target = None
    parent = combo.parentWidget()
    while parent is not None:
        if isinstance(parent, QAbstractScrollArea):
            target = parent
            break
        parent = parent.parentWidget()
    assert target is not None
    assert target.verticalScrollBar().maximum() > 0
    target.verticalScrollBar().setValue(0)
    combo.blockSignals(True)
    combo.setCurrentIndex(0)
    _wheel(dashboard, combo, delta=-240)
    assert target.verticalScrollBar().value() > 0


def test_wheel_filter_ignores_combo_with_open_popup(dashboard, monkeypatch):
    from ui.flowpilot_dashboard import _wheel_guard
    assert _wheel_guard is not None
    combo = dashboard.home_page.visibility_choice

    class FakeView:
        def isVisible(self):
            return True

    monkeypatch.setattr(combo, "view", lambda: FakeView())
    combo.blockSignals(True)
    combo.setCurrentIndex(0)
    event = _wheel(dashboard, combo, delta=120)
    assert _wheel_guard.eventFilter(combo, event) is False


def test_insights_view_shows_dashes_until_real_data(tmp_path):
    from engine.insights_engine import InsightsEngine
    from ui.insights_view import InsightsView
    engine = InsightsEngine(storage_path=tmp_path / "insights.json")
    view = InsightsView(parent=None, engine=engine)
    assert view.val_words.text() == "0"
    assert view.val_wpm.text() == "—"
    assert view.val_streak.text() == "—"
    assert view.val_deep_work.text() == "—"
    engine.record_dictation("six fresh words are now real data", duration_sec=2.4)
    view.refresh_metrics()
    assert view.val_wpm.text().endswith("wpm")
    assert view.val_streak.text().endswith("days")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
