"""Feature 20 companion visibility contract, covers AC-1 through AC-10."""

import os
import sys
from pathlib import Path

os.environ.setdefault("FLOWPILOT_HEADLESS", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from PySide6.QtWidgets import QApplication

from engine.companion_store import CompanionStore
from engine.companion_visibility import ContextSnapshot, decide_visibility
from engine.preference_learning import PreferenceLearningEngine
from ui.companion_visibility_controller import CompanionVisibilityController
from ui.floating_hud import FloatingHUD


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def profile(tmp_path):
    return CompanionStore(tmp_path), PreferenceLearningEngine(tmp_path)


def test_ac1_old_visibility_migrates_without_losing_character_or_position(tmp_path):
    path = tmp_path / "companion.json"
    path.write_text('{"visible":false,"selected_asset_id":"kiki","hud_x":321,"hud_y":456,"cat_sound":false}', encoding="utf-8")
    store = CompanionStore(tmp_path)
    assert store.get("visibility_mode") == "hidden"
    assert store.get("selected_asset_id") == "kiki"
    assert (store.get("hud_x"), store.get("hud_y"), store.get("cat_sound")) == (321, 456, False)
    assert CompanionStore(tmp_path).get_all() == store.get_all()


def test_ac1_old_visible_true_is_explicit_always_show(tmp_path):
    (tmp_path / "companion.json").write_text('{"visible":true,"selected_asset_id":"nimbus"}', encoding="utf-8")
    store = CompanionStore(tmp_path)
    assert store.get("visibility_mode") == "always"
    assert store.get("selected_asset_id") == "nimbus"


def test_ac1_old_profile_without_visibility_uses_smart_default(tmp_path):
    (tmp_path / "companion.json").write_text('{"selected_asset_id":"nimbus"}', encoding="utf-8")
    assert CompanionStore(tmp_path).get("visibility_mode") == "smart"


def test_ac1_new_profile_defaults_smart_and_hide_restores_prior_choice(profile):
    store, _ = profile
    assert store.get("visibility_mode") == "smart"
    store.set_visibility_mode("always")
    store.set_visibility_mode("hidden")
    assert store.get("last_visible_mode") == "always"
    assert CompanionStore(store.storage_dir).get("visible") is False
    with pytest.raises(ValueError):
        store.set_visibility_mode("sometimes")


def test_ac2_ac3_fullscreen_presentation_and_maximized_editor_policy():
    fullscreen = ContextSnapshot(51, "chrome.exe", True, 5, True)
    maximized = ContextSnapshot(52, "code.exe", False, 5, True)
    presentation = ContextSnapshot(53, "powerpnt.exe", False, 4, True)
    assert decide_visibility("smart", fullscreen).presentation == "hidden"
    assert decide_visibility("smart", presentation).presentation == "hidden"
    assert decide_visibility("smart", maximized).presentation == "edge"
    assert decide_visibility("always", fullscreen).presentation == "normal"
    assert decide_visibility("hidden", maximized).presentation == "hidden"


def test_ac3_context_monitor_separates_borderless_fullscreen_from_maximized(monkeypatch):
    import types
    import engine.window_inspector as window_inspector

    if not window_inspector.HAS_WIN32:
        pytest.skip("Win32 geometry APIs unavailable")
    window = {"style": 0, "zoomed": False}
    gui = window_inspector.win32gui
    api = window_inspector.win32api
    monkeypatch.setattr(gui, "GetForegroundWindow", lambda: 777)
    monkeypatch.setattr(api, "MonitorFromWindow", lambda *_: 10)
    monkeypatch.setattr(api, "GetMonitorInfo", lambda *_: {"Monitor": (0, 0, 1920, 1080)})
    monkeypatch.setattr(gui, "GetWindowRect", lambda *_: (0, 0, 1920, 1080))
    monkeypatch.setattr(gui, "GetWindowLong", lambda *_: window["style"])
    monkeypatch.setattr(gui, "GetWindowPlacement", lambda *_: (0, 3 if window["zoomed"] else 1, None, None, None))
    monkeypatch.setattr(window_inspector.win32process, "GetWindowThreadProcessId", lambda *_: (1, 123000))
    monkeypatch.setattr(window_inspector.psutil, "Process", lambda *_: types.SimpleNamespace(name=lambda: "code.exe"))
    shell = types.SimpleNamespace(SHQueryUserNotificationState=lambda value: 1)
    monkeypatch.setattr(window_inspector.ctypes, "windll", types.SimpleNamespace(shell32=shell))
    monitor = window_inspector.ContextMonitor()
    assert monitor.sample().fullscreen is True
    window.update(style=0x00C00000, zoomed=True)
    assert monitor.sample().fullscreen is False


def test_ac4_app_rules_win_over_quiet_defaults_but_not_fullscreen():
    editor = ContextSnapshot(21, "code.exe", False, 5, True)
    assert decide_visibility("smart", editor, "normal").presentation == "normal"
    assert decide_visibility("smart", editor, "hidden").presentation == "hidden"
    assert decide_visibility("smart", ContextSnapshot(21, "code.exe", True, 5, True), "normal").presentation == "hidden"
    assert decide_visibility("smart", editor, "bogus").presentation == "edge"


class FakeHUD:
    def __init__(self):
        self.visible = False
        self.presentation = "normal"
        self.calls = []

    def isVisible(self):
        return self.visible

    def show(self):
        self.visible = True
        self.calls.append("show")

    def hide(self):
        self.visible = False
        self.calls.append("hide")

    def set_presentation(self, presentation):
        self.presentation = presentation
        self.calls.append(presentation)

    def _sync_animation_timer(self):
        pass

    def raise_(self):
        pass


class FakeMonitor:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def sample(self):
        return self.snapshot


def test_ac2_ac3_ac5_controller_debounces_and_preserves_fullscreen_on_unknown(app, profile, monkeypatch):
    store, learning = profile
    monkeypatch.setenv("FLOWPILOT_CONFIG_DIR", str(store.storage_dir))
    hud = FakeHUD()
    monitor = FakeMonitor(ContextSnapshot(90, "chrome.exe", False, 5, True))
    controller = CompanionVisibilityController(hud, store, learning, monitor=monitor)
    controller.refresh(force=True)
    assert hud.visible
    monitor.snapshot = ContextSnapshot(90, "chrome.exe", True, 5, True)
    controller.refresh()
    assert hud.visible  # First sample is deliberately not enough.
    controller.refresh()
    assert not hud.visible
    monitor.snapshot = ContextSnapshot()
    controller.refresh()
    assert not hud.visible
    assert hud.calls.count("hide") == 1
    monitor.snapshot = ContextSnapshot(91, "notepad.exe", False, 5, True)
    controller.refresh()
    controller.refresh()
    assert hud.visible


def test_ac5_temporary_show_expires_on_real_foreground_change(app, profile):
    store, learning = profile
    hud = FakeHUD()
    monitor = FakeMonitor(ContextSnapshot(90, "chrome.exe", True, 5, True))
    controller = CompanionVisibilityController(hud, store, learning, monitor=monitor)
    controller.refresh(force=True)
    assert not hud.visible
    controller.show_now()
    assert hud.visible
    monitor.snapshot = ContextSnapshot(91, "vlc.exe", True, 5, True)
    controller.refresh()
    controller.refresh()
    assert not hud.visible


def test_ac5_tray_toggle_restores_hidden_mode_even_during_fullscreen(app, profile):
    store, learning = profile
    store.set_visibility_mode("hidden")
    hud = FakeHUD()
    monitor = FakeMonitor(ContextSnapshot(90, "chrome.exe", True, 5, True))
    controller = CompanionVisibilityController(hud, store, learning, monitor=monitor)
    controller.refresh(force=True)
    controller.toggle()
    assert store.get("visibility_mode") == "smart"
    assert hud.visible


def test_ac5_show_now_restores_hidden_mode_even_during_fullscreen(app, profile):
    store, learning = profile
    store.set_visibility_mode("hidden")
    hud = FakeHUD()
    monitor = FakeMonitor(ContextSnapshot(90, "chrome.exe", True, 5, True))
    controller = CompanionVisibilityController(hud, store, learning, monitor=monitor)
    controller.refresh(force=True)
    controller.show_now()
    assert store.get("visibility_mode") == "smart"
    assert hud.visible
    assert controller.current.reason == "Temporarily shown by you"


def test_ac7_hud_stops_animation_when_hidden_edge_or_reduced(app, monkeypatch, tmp_path):
    import engine.companion_store as companion_store
    monkeypatch.setattr(companion_store, "_store_instance", CompanionStore(tmp_path))
    hud = FloatingHUD()
    try:
        assert not hud._anim_timer.isActive()
        hud.show()
        assert hud._anim_timer.isActive()
        hud.set_presentation("edge")
        assert not hud._anim_timer.isActive()
        assert hud._visual_style == "kitty"
        hud.set_presentation("normal")
        assert hud._anim_timer.isActive()
        hud._reduced_motion = True
        hud._sync_animation_timer()
        assert not hud._anim_timer.isActive()
        hud.hide()
        assert not hud._anim_timer.isActive()
    finally:
        hud.close()


def test_ac9_approved_rules_are_snapshots_and_learning_requires_consent(profile):
    _, learning = profile
    learning.record_setting_action("code.exe", "companion_visibility", "edge")
    assert learning.get_proposals() == []
    learning.set_approved_rule("code.exe", "companion_visibility", "edge")
    rules = learning.get_approved_rules()
    rules["code.exe"]["companion_visibility"] = "hidden"
    assert learning.get_approved_rules()["code.exe"]["companion_visibility"] == "edge"
    with pytest.raises(ValueError):
        learning.set_approved_rule("code.exe", "companion_visibility", "invalid")


def test_ac9_auto_hide_never_counts_as_a_manual_learning_choice(app, profile):
    store, learning = profile
    learning.set_enabled(True)
    hud = FakeHUD()
    monitor = FakeMonitor(ContextSnapshot(31, "chrome.exe", True, 5, True))
    controller = CompanionVisibilityController(hud, store, learning, monitor=monitor)
    controller.refresh(force=True)
    assert learning.load()["observations"] == []
    monitor.snapshot = ContextSnapshot(32, "code.exe", False, 5, True)
    controller.set_mode("hidden")
    observations = learning.load()["observations"]
    assert len(observations) == 1
    assert observations[0]["app_id"] == "code.exe"
    assert observations[0]["value"] == "hidden"


def test_ac1_setting_save_failure_keeps_previous_mode(profile, monkeypatch):
    store, _ = profile
    monkeypatch.setattr(store, "_persist_unlocked", lambda: False)
    with pytest.raises(OSError):
        store.set_visibility_mode("hidden")
    assert store.get("visibility_mode") == "smart"


def test_ac8_studio_exposes_keyboard_named_visibility_and_app_rule_controls(app, profile, monkeypatch):
    import engine.companion_store as companion_store
    import engine.preference_learning as preference_learning
    from ui.companion_studio import CompanionStudioDialog

    store, learning = profile
    monkeypatch.setenv("FLOWPILOT_CONFIG_DIR", str(store.storage_dir))
    monkeypatch.setattr(companion_store, "_store_instance", store)
    monkeypatch.setattr(preference_learning, "_learning_instance", learning)
    studio = CompanionStudioDialog()
    try:
        assert studio.combo_visibility.accessibleName() == "Desktop companion visibility"
        assert studio.txt_visibility_app.accessibleName() == "Application executable name"
        studio.combo_visibility.setCurrentIndex(studio.combo_visibility.findData("always"))
        studio._on_apply_clicked()
        assert store.get("visibility_mode") == "always"
        studio.txt_visibility_app.setText("code.exe")
        studio.combo_app_visibility.setCurrentIndex(studio.combo_app_visibility.findData("edge"))
        studio._on_save_app_visibility()
        assert learning.get_approved_rules()["code.exe"]["companion_visibility"] == "edge"
    finally:
        studio.close()


def test_ac4_media_audio_hides_smart_but_respects_manual_wins_and_rules():
    chrome = ContextSnapshot(41, "chrome.exe", False, 5, True)
    assert decide_visibility("smart", chrome, media=True).presentation == "hidden"
    assert decide_visibility("smart", chrome, media=True).reason == "Media audio playing"
    assert decide_visibility("always", chrome, media=True).presentation == "normal"
    assert decide_visibility("hidden", chrome, media=True).presentation == "hidden"
    assert decide_visibility("smart", chrome, "normal", media=True).presentation == "normal"
    assert decide_visibility("smart", chrome, "hidden", media=True).presentation == "hidden"
    shown = ContextSnapshot(41, "chrome.exe", False, 5, True)
    assert decide_visibility("smart", shown, show_now_hwnd=41, media=True).presentation == "normal"
    editor = ContextSnapshot(42, "code.exe", False, 5, True)
    assert decide_visibility("smart", editor, media=True).presentation == "edge"


class FakePresence:
    def __init__(self, active=False):
        self.active = active

    def is_active(self):
        return self.active


def test_ac6_media_presence_hides_until_quiet_and_heeds_dictation(app, profile):
    store, learning = profile
    hud = FakeHUD()
    monitor = FakeMonitor(ContextSnapshot(90, "chrome.exe", False, 5, True))
    presence = FakePresence(active=True)
    controller = CompanionVisibilityController(hud, store, learning, monitor=monitor, media=presence)
    controller.refresh(force=True)
    assert not hud.visible
    assert controller.current.reason == "Media audio playing"
    presence.active = False
    controller.refresh(force=True)
    assert hud.visible
    presence.active = True
    controller.set_state_hint({"state": "listening"})
    controller.refresh(force=True)
    assert hud.visible
    controller.set_state_hint({"state": "idle"})
    controller.refresh(force=True)
    assert not hud.visible


def test_media_presence_grace_and_audibility_rules_without_com():
    from engine.media_presence import NullMediaPresence, SessionSample, MediaAudioPresence

    tick = [0.0]
    clock = lambda: tick[0]  # noqa: E731
    samples = [SessionSample(1, "vlc.exe", 0.5, 1.0)]
    presence_active = MediaAudioPresence(
        grace_seconds=1.5, sustain_seconds=1.0, provider=lambda: samples, clock=clock,
    )
    assert presence_active.is_active() is False  # one audible probe: not yet sustained

    sustained = MediaAudioPresence(sustain_seconds=0.0, provider=lambda: samples, clock=clock)
    assert sustained.is_active() is True

    samples[0] = SessionSample(1, "vlc.exe", 0.0, 1.0)  # playback went silent
    tick[0] = 1.0
    assert sustained.is_active() is True  # within the 1.5 s linger
    tick[0] = 1.51
    assert sustained.is_active() is False  # quiet for longer than grace

    # The classic false hide: a short system sound blip must not hide anything.
    blip = [SessionSample(2, "audiodg-ish.exe", 0.5, 1.0)]
    short_noise = MediaAudioPresence(
        grace_seconds=1.5, sustain_seconds=1.0,
        provider=lambda: blip, clock=clock,
    )
    tick[0] = 5.0
    assert short_noise.is_active() is False  # single audible tick, no continuity
    blip[0] = SessionSample(2, "blip.exe", 0.0, 1.0)
    assert short_noise.is_active() is False  # silence drops the suspicion
    silent_source = MediaAudioPresence(grace_seconds=0.0, provider=lambda: [], clock=clock)
    assert silent_source.is_active() is False
    volume_zero = MediaAudioPresence(
        sustain_seconds=0.0,
        provider=lambda: [SessionSample(2, "vlc.exe", 0.5, 0.0)],
        clock=clock,
    )
    assert volume_zero.is_active() is False
    broken = MediaAudioPresence(grace_seconds=0.0, provider=lambda: (_ for _ in ()).throw(RuntimeError("com")), clock=clock)
    assert broken.is_active() is False
    assert broken.is_active() is False  # permanently disabled after the error
    assert NullMediaPresence().is_active() is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
