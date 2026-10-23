"""Feature 20: single Qt owner for FlowPilot companion visibility."""

import time

from PySide6.QtCore import QObject, QTimer, Signal

from engine.companion_visibility import ContextSnapshot, VisibilityDecision, decide_visibility
from engine.window_inspector import ContextMonitor


class CompanionVisibilityController(QObject):
    decision_changed = Signal(str, str)
    error = Signal(str)

    def __init__(self, hud, store, learning, parent=None, monitor=None):
        super().__init__(parent)
        self.hud = hud
        self.store = store
        self.learning = learning
        self.monitor = monitor or ContextMonitor()
        self.current = VisibilityDecision("hidden", "Starting")
        self._stable = ContextSnapshot()
        self._unknown_since = None
        self._candidate = None
        self._candidate_count = 0
        self._show_now_hwnd = 0
        self._timer = QTimer(self)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self.refresh)

    def start(self):
        self.refresh(force=True)
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def set_mode(self, mode: str):
        try:
            self.store.set_visibility_mode(mode)
        except (OSError, ValueError) as exc:
            self.error.emit(str(exc))
            return
        if mode in ("always", "hidden"):
            self._observe_manual_choice("normal" if mode == "always" else "hidden")
        self._show_now_hwnd = 0
        self.refresh(force=True)

    def toggle(self):
        mode = self.store.get("visibility_mode", "smart")
        if mode == "hidden":
            self.set_mode(self.store.get("last_visible_mode", "smart"))
            if self.current.presentation == "hidden" and self.store.get("visibility_mode") != "hidden":
                self.show_now()
        elif self.current.presentation == "hidden":
            self.show_now()
        else:
            self.set_mode("hidden")

    def show_now(self):
        if self.store.get("visibility_mode") == "hidden":
            self.set_mode(self.store.get("last_visible_mode", "smart"))
            if self.store.get("visibility_mode") == "hidden":
                return
        snapshot = self.monitor.sample()
        self._observe_manual_choice("normal", snapshot)
        self._show_now_hwnd = snapshot.hwnd if snapshot.known and not snapshot.own_app else self._stable.hwnd
        self.refresh(force=True)
        if self.hud.isVisible():
            self.hud.raise_()

    def _observe_manual_choice(self, presentation: str, snapshot=None):
        snapshot = snapshot or self.monitor.sample()
        if (snapshot.known and not snapshot.own_app and not snapshot.fullscreen
                and snapshot.shell_state not in (2, 3, 4)):
            self.learning.record_setting_action(
                snapshot.process_name, "companion_visibility", presentation
            )

    def set_app_rule(self, app_name: str, presentation: str):
        app_name = app_name.strip().lower()
        if not app_name.endswith(".exe") or any(c in app_name for c in "\\/:"):
            raise ValueError("Enter an executable name such as code.exe")
        if presentation not in ("normal", "edge", "hidden"):
            raise ValueError("Invalid app presentation")
        try:
            self.learning.set_approved_rule(app_name, "companion_visibility", presentation)
        except OSError as exc:
            self.error.emit(str(exc))
            return
        self.refresh(force=True)

    def forget_app_rule(self, app_name: str):
        self.learning.forget_rule(app_name, "companion_visibility")
        self.refresh(force=True)

    def refresh(self, force=False):
        snapshot = self.monitor.sample()
        now = time.monotonic()
        if snapshot.own_app:
            snapshot = self._stable if self._stable.known else ContextSnapshot(shell_state=snapshot.shell_state)
        if snapshot.known:
            if self._show_now_hwnd and snapshot.hwnd != self._show_now_hwnd:
                self._show_now_hwnd = 0
            identity = (snapshot.hwnd, snapshot.fullscreen, snapshot.shell_state)
            if identity == self._candidate:
                self._candidate_count += 1
            else:
                self._candidate = identity
                self._candidate_count = 1
            if force or self._candidate_count >= 2:
                self._stable = snapshot
                self._unknown_since = None
        else:
            if self._unknown_since is None:
                self._unknown_since = now
            # Keep a known fullscreen decision during transient focus loss.
            if now - self._unknown_since <= 0.75 and self._stable.known:
                snapshot = self._stable
            else:
                self._stable = ContextSnapshot(shell_state=snapshot.shell_state)
                self._show_now_hwnd = 0
        if snapshot.known and not force and self._candidate_count < 2:
            snapshot = self._stable
        approved = self.learning.get_approved_rules()
        rule = approved.get(snapshot.process_name, {}).get("companion_visibility")
        decision = decide_visibility(
            self.store.get("visibility_mode", "smart"), snapshot, rule, self._show_now_hwnd
        )
        self.apply(decision)

    def apply(self, decision: VisibilityDecision):
        if decision != self.current:
            self.current = decision
            if decision.presentation == "hidden":
                if self.hud.isVisible():
                    self.hud.hide()
            else:
                self.hud.set_presentation(decision.presentation)
                if not self.hud.isVisible():
                    self.hud.show()
            self.decision_changed.emit(decision.presentation, decision.reason)
        elif decision.presentation != "hidden":
            self.hud._sync_animation_timer()
