"""Read only FlowPilot UI audit using an isolated Qt profile."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QComboBox, QMessageBox, QPushButton, QScrollArea


def wheel_down(widget):
    point = QPointF(widget.rect().center())
    event = QWheelEvent(
        point,
        QPointF(widget.mapToGlobal(QPoint(int(point.x()), int(point.y())))),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.ScrollUpdate,
        False,
    )
    QApplication.sendEvent(widget, event)
    QApplication.processEvents()


def probe_combos(host, label):
    for combo in host.findChildren(QComboBox):
        if not combo.isVisibleTo(host) or combo.count() < 2:
            continue
        start = 1 if combo.count() > 2 else 0
        combo.setCurrentIndex(start)
        QApplication.processEvents()
        combo.setFocus()
        QApplication.processEvents()
        before = combo.currentIndex()
        wheel_down(combo)
        after = combo.currentIndex()
        print(f"WHEEL {label} {combo.objectName() or combo.toolTip() or combo.currentText()!r}: {before}->{after} changed={before != after}")
        combo.setCurrentIndex(start)


def click_named(host, text):
    button = next(item for item in host.findChildren(QPushButton) if text in item.text())
    assert button.isEnabled(), f"{text} unexpectedly disabled"
    button.click()
    QApplication.processEvents()
    return button


def probe_safe_actions(window):
    window.nav_group.button(0).click()
    home = window.home_page
    bar = home.verticalScrollBar()
    before_scroll = bar.value()
    wheel_down(home.viewport())
    print(f"SCROLL Home: max={bar.maximum()} visible={bar.isVisible()} "
          f"wheel_value={before_scroll}->{bar.value()}")
    observed_modes = []
    window.companion_visibility_requested.connect(observed_modes.append)
    home.visibility_choice.setCurrentIndex(0)
    home.visibility_choice.setFocus()
    wheel_down(home.visibility_choice)
    print(f"WHEEL Home companion mode: index={home.visibility_choice.currentIndex()} "
          f"emitted={observed_modes}")
    home.visibility_choice.setCurrentIndex(0)
    routes = (("Open Scratchpad", 3), ("Open Notetaker", 4),
              ("View Analytics", 5), ("Customize Appearance", 8),
              ("Adjust settings", 9))
    for text, destination in routes:
        window.nav_group.button(0).click()
        click_named(window.home_page, text)
        assert window.stack.currentIndex() == destination
        print(f"ACTION Home {text!r}: opened page {destination}")

    window.nav_group.button(1).click()
    transforms = window.transforms_view
    transforms.edit_original.setPlainText("Please write this short message for me.")
    click_named(transforms, "Make Concise")
    assert transforms.edit_transformed.toPlainText()
    print("ACTION Text edits 'Make Concise': produced a preview")
    assert not transforms.btn_replace.isEnabled() and not transforms.btn_revert.isEnabled()

    window.nav_group.button(2).click()
    dictionary = window.dictionary_view
    dictionary.input_term.setText("FlowPilotAuditToken")
    dictionary.input_alias.setText("flow pilot audit token")
    click_named(dictionary, "Add to Dictionary")
    dictionary.input_search.setText("FlowPilotAuditToken")
    assert dictionary.table.rowCount() == 1
    dictionary.table.cellWidget(0, 4).click()
    assert dictionary.table.rowCount() == 0
    print("ACTION Dictionary add, search and delete: updated isolated profile")

    window.nav_group.button(3).click()
    pad = window.scratchpad_view
    pad.editor.setPlainText("alpha\nbeta")
    click_named(pad, "Bulletize")
    assert pad.editor.toPlainText() == "- alpha\n- beta"
    pad.btn_voice_edit.click()
    assert pad.edit_panel.isVisible()
    pad.btn_voice_edit.click()
    assert not pad.edit_panel.isVisible()
    with patch("ui.scratchpad_view.QMessageBox.question", return_value=QMessageBox.Yes):
        click_named(pad, "Clear")
    assert not pad.editor.toPlainText()
    pad.btn_undo_clear.click()
    assert pad.editor.toPlainText() == "- alpha\n- beta"
    print("ACTION Scratchpad bulletize, voice panel, clear and undo: worked")

    window.nav_group.button(4).click()
    meetings = window.notetaker_view
    meetings.btn_translate.click()
    assert meetings.btn_translate.isChecked()
    meetings.btn_translate.click()
    assert not meetings.btn_translate.isChecked()
    print("ACTION Meetings translation toggle: on then off")

    window.nav_group.button(5).click()
    click_named(window.insights_view, "Refresh")
    assert window.insights_view.val_words.text()
    print("ACTION Insights refresh: metrics rendered")

    window.nav_group.button(6).click()
    snippets = window.snippets_view
    snippets.input_trigger.setText("flowpilot audit trigger")
    snippets.input_expansion.setPlainText("A private audit expansion")
    click_named(snippets, "Add Snippet")
    snippets.input_search.setText("flowpilot audit trigger")
    assert snippets.table.rowCount() == 1
    snippets.table.cellWidget(0, 2).click()
    assert snippets.table.rowCount() == 0
    print("ACTION Snippets add, search and delete: updated isolated profile")

    window.nav_group.button(7).click()
    history = window.history_view
    click_named(history, "Starred Only")
    assert history._star_filter
    click_named(history, "Starred Only")
    assert not history._star_filter
    print("ACTION History starred filter: on then off")

    window.nav_group.button(8).click()
    studio = window.stack.currentWidget()
    emitted = []
    window.show_companion_requested.connect(lambda: emitted.append(True))
    studio.btn_show_live.click()
    assert emitted
    studio.btn_cancel.click()
    assert window.stack.currentIndex() == 0
    print("ACTION Studio show request and Cancel: signal and navigation worked")

    window.nav_group.button(9).click()
    settings = window.stack.currentWidget()
    for index in range(settings.tabs.count()):
        settings.tabs.setCurrentIndex(index)
        assert settings.tabs.currentIndex() == index
    click_named(settings, "Cancel")
    assert window.stack.currentIndex() == 0
    print("ACTION Settings three tabs and Cancel: worked")


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "scratch" / "ui-audit-20261023"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="flowpilot-ui-audit-") as isolated:
        profile = Path(isolated)
        os.environ["FLOWPILOT_CONFIG_DIR"] = str(profile)
        os.environ["FLOWPILOT_CONFIG_FILE"] = str(profile / "config.json")
        with patch.object(Path, "home", lambda: profile), \
             patch("sounddevice.query_devices", return_value=[]), \
             patch("sounddevice.InputStream", side_effect=AssertionError("UI audit must not open a microphone")), \
             patch("engine.stt_engine.STTEngine._get_local_model", side_effect=AssertionError("UI audit must not load a model")):
            from ui.flowpilot_dashboard import FlowPilotDashboard
            app = QApplication.instance() or QApplication([])
            window = FlowPilotDashboard(config={
                "hotkey": "F9", "language": "en", "local_model_size": "base",
                "save_history_text": False, "ui_theme": "sand",
            })
            try:
                for width, height in ((1160, 820), (880, 580)):
                    window.resize(width, height)
                    window.show()
                    app.processEvents()
                    for index in range(window.stack.count()):
                        button = window.nav_group.button(index)
                        button.click()
                        app.processEvents()
                        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                        app.processEvents()
                        page = window.stack.currentWidget()
                        shown = [item for item in page.findChildren(QPushButton)
                                 if item.isVisibleTo(window)]
                        clipped = []
                        narrow = []
                        for item in shown:
                            bounds = item.rect().translated(item.mapTo(window, QPoint(0, 0)))
                            if not window.rect().intersects(bounds):
                                clipped.append(item.text())
                            if item.fontMetrics().horizontalAdvance(item.text()) > item.width() - 24:
                                narrow.append(item.text())
                        path = output / f"page-{index}-{width}x{height}.png"
                        window.grab().save(str(path))
                        print(f"PAGE {index} {button.text()!r} {width}x{height}: "
                              f"active={page.__class__.__name__} buttons={len(shown)} "
                              f"outside_window={clipped} narrow={narrow} screenshot={path.name}")
                    if width == 880:
                        window.nav_group.button(9).click()
                        settings = window.stack.currentWidget()
                        settings.tabs.setCurrentIndex(0)
                        app.processEvents()
                        general = next(area for area in settings.findChildren(QScrollArea)
                                       if area.isVisibleTo(settings))
                        print(f"SCROLL Settings: max={general.verticalScrollBar().maximum()}")
                        probe_combos(settings, "Settings")
                        window.nav_group.button(8).click()
                        studio = window.stack.currentWidget()
                        for tab_index in range(studio.tabs.count()):
                            studio.tabs.setCurrentIndex(tab_index)
                            app.processEvents()
                            print(f"TAB Studio {tab_index} {studio.tabs.tabText(tab_index)!r}: "
                                  f"buttons={len([item for item in studio.tabs.currentWidget().findChildren(QPushButton) if item.isVisibleTo(studio)])}")
                            probe_combos(studio.tabs.currentWidget(), f"Studio {studio.tabs.tabText(tab_index)}")
                        probe_safe_actions(window)
            finally:
                window.scratchpad_view._autosave_timer.stop()
                window.close()
                app.processEvents()


if __name__ == "__main__":
    main()
