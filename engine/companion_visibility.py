"""Feature 20: pure, privacy-limited companion presentation policy."""

from dataclasses import dataclass
from typing import Optional


QUIET_APPS = frozenset({
    "code.exe", "cursor.exe", "devenv.exe", "pycharm64.exe", "idea64.exe",
    "notepad++.exe", "windowsterminal.exe", "wt.exe", "cmd.exe",
    "powershell.exe", "pwsh.exe", "wezterm-gui.exe", "alacritty.exe",
})
PRESENTATION_STATES = frozenset({2, 3, 4})  # QUNS_BUSY, D3D_FULLSCREEN, PRESENTATION_MODE


@dataclass(frozen=True)
class ContextSnapshot:
    hwnd: int = 0
    process_name: str = ""
    fullscreen: bool = False
    shell_state: Optional[int] = None
    known: bool = False
    own_app: bool = False


@dataclass(frozen=True)
class VisibilityDecision:
    presentation: str
    reason: str


def decide_visibility(
    mode: str,
    context: ContextSnapshot,
    app_rule: Optional[str] = None,
    show_now_hwnd: int = 0,
) -> VisibilityDecision:
    """Only explicit intent or a verified local context may hide the companion."""
    if mode == "hidden":
        return VisibilityDecision("hidden", "Hidden by you")
    if mode == "always":
        return VisibilityDecision("normal", "Always show")
    if mode != "smart":
        mode = "smart"
    if context.known and show_now_hwnd and context.hwnd == show_now_hwnd:
        return VisibilityDecision("normal", "Temporarily shown by you")
    if context.shell_state in PRESENTATION_STATES:
        return VisibilityDecision("hidden", "Windows presentation or fullscreen mode")
    if context.known and context.fullscreen:
        return VisibilityDecision("hidden", "Foreground app is fullscreen")
    if context.known:
        if app_rule in ("normal", "edge", "hidden"):
            return VisibilityDecision(app_rule, f"App rule: {context.process_name}")
        if context.process_name in QUIET_APPS:
            return VisibilityDecision("edge", "Quiet editor or terminal")
    return VisibilityDecision("normal", "Smart default")
