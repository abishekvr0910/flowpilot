"""Original native workspace themes. No web assets, downloads or dependencies."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout


_DARK_STYLE = """
QMainWindow, QDialog, QWidget#WorkspacePage { background: #101715; color: #edf3ee; }
QWidget { font-family: 'Segoe UI'; font-size: 13px; }
QLabel { color: #edf3ee; background: transparent; border: none; }
QLabel[role="muted"] { color: #a5b5ac; }
QLabel[role="eyebrow"] { color: #a5b5ac; font-size: 11px; font-weight: 600; }
QLabel[role="title"] { font-size: 28px; font-weight: 600; }
QLabel[role="hero"] { font-size: 34px; font-weight: 600; }
QLabel[role="section"] { font-size: 17px; font-weight: 600; }
QLabel[role="shortcut"] { color: #c4efd0; font-size: 25px; font-weight: 600; }
QLabel[role="metric"] { font-family: 'Georgia'; font-size: 32px; font-weight: 600; }
QFrame[role="surface"] { background: #19241f; border: 1px solid #304139; border-radius: 16px; }
QFrame[role="heroSurface"] { background: #203129; border: 1px solid #3c5446; border-radius: 18px; }
QWidget#Sidebar { background: #141e19; border-right: 1px solid #304139; }
QPushButton, QToolButton {
    color: #edf3ee; background: #24332b; border: 1px solid #405449;
    border-radius: 8px; padding: 9px 14px; font-weight: 600;
}
QPushButton:hover, QToolButton:hover { background: #30473a; border-color: #8cae98; }
QPushButton:focus, QToolButton:focus, QComboBox:focus, QLineEdit:focus { border: 2px solid #b8eac6; }
QPushButton:disabled, QToolButton:disabled { color: #84958b; background: #1b2720; border-color: #304139; }
QPushButton#primaryBtn { background: #c4efd0; color: #122319; border-color: #c4efd0; }
QPushButton#primaryBtn:hover { background: #dbf8e2; }
QPushButton[role="nav"] { text-align: left; background: transparent; border: 1px solid transparent; padding: 9px 12px; color: #a5b5ac; }
QPushButton[role="nav"]:hover { background: #24332b; color: #edf3ee; }
QPushButton[role="nav"]:checked { background: #2a4033; color: #d2f6dc; border-color: #405449; }
QPushButton[role="nav"]:focus { border-color: #b8eac6; }
QToolButton[role="companionTile"] { background: #19241f; padding: 10px; }
QToolButton[role="companionTile"]:checked { background: #2a4033; border: 2px solid #b8eac6; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QTableWidget {
    background: #111b16; color: #edf3ee; border: 1px solid #405449;
    border-radius: 7px; padding: 8px; selection-background-color: #405f4c; selection-color: #ffffff;
}
QComboBox QAbstractItemView { background: #19241f; color: #edf3ee; selection-background-color: #405f4c; }
QCheckBox, QRadioButton { color: #edf3ee; spacing: 9px; padding: 3px; }
QTabWidget::pane { border: none; background: #101715; }
QTabBar::tab { color: #a5b5ac; background: #141e19; padding: 10px 14px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #c4efd0; border-bottom-color: #c4efd0; }
QTabBar::tab:hover { background: #24332b; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: #141e19; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #52695b; min-height: 28px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QHeaderView::section { background: #24332b; color: #a5b5ac; border: none; padding: 8px; }
QToolTip { background: #edf3ee; color: #101715; border: 1px solid #405449; padding: 6px; }
"""


_SAND_COLORS = {
    "#101715": "#f5f4f0", "#edf3ee": "#252923", "#a5b5ac": "#656a62",
    "#c4efd0": "#d98925", "#19241f": "#ffffff", "#304139": "#e8e6df",
    "#203129": "#fffaf2", "#3c5446": "#e7dfd2", "#141e19": "#faf9f5",
    "#24332b": "#ffffff", "#405449": "#dedbd2", "#30473a": "#fff1dc",
    "#8cae98": "#d98925", "#b8eac6": "#bd6a08", "#84958b": "#898d86",
    "#1b2720": "#f0efea", "#122319": "#30210e", "#dbf8e2": "#ffbc6c",
    "#2a4033": "#fff0d6", "#d2f6dc": "#614017", "#111b16": "#ffffff",
    "#405f4c": "#ffdcaa", "#52695b": "#c7c4ba",
}


def _replace_colors(css, colors):
    import re
    return re.sub(
        r"#[0-9a-fA-F]{6}\b",
        lambda match: colors.get(match.group(0).lower(), match.group(0)),
        css,
    )


def workspace_style(theme="sand"):
    """Return the shared QSS for the selected local appearance."""
    if theme == "obsidian":
        return _DARK_STYLE
    return _replace_colors(_DARK_STYLE, _SAND_COLORS)


WORKSPACE_STYLE = workspace_style()


def label(text, role="muted", parent=None):
    widget = QLabel(text, parent)
    widget.setProperty("role", role)
    widget.setTextFormat(Qt.PlainText)
    widget.setWordWrap(True)
    return widget


def surface(role="surface"):
    frame = QFrame()
    frame.setProperty("role", role)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(12)
    return frame, layout


def harmonize_legacy_styles(root, theme="sand", *, include_root=True):
    """Recolor existing widget-local QSS without changing semantic warning colors.

    Original declarations are retained so switching themes never recolors an already
    recolored value or loses a widget's own control-specific styling.
    """
    from PySide6.QtWidgets import QWidget
    legacy_to_dark = {
        "#0b0f19": "#101715", "#0f172a": "#111b16", "#1e293b": "#19241f",
        "#334155": "#304139", "#475569": "#405449", "#94a3b8": "#a5b5ac",
        "#64748b": "#a5b5ac", "#cbd5e1": "#edf3ee", "#e2e8f0": "#edf3ee",
        "#f8fafc": "#edf3ee", "#38bdf8": "#c4efd0", "#0284c7": "#405f4c",
        "#0369a1": "#405f4c", "#243247": "#24332b", "#131e33": "#141e19",
    }
    colors = {key: (_SAND_COLORS.get(value, value) if theme != "obsidian" else value)
              for key, value in legacy_to_dark.items()}
    if theme != "obsidian":
        colors.update(_SAND_COLORS)
    widgets = ([root] if include_root else []) + root.findChildren(QWidget)
    for widget in widgets:
        original = widget.property("_fp_original_qss")
        if original is None:
            original = widget.styleSheet()
            widget.setProperty("_fp_original_qss", original)
        if original:
            recolored = _replace_colors(original, colors)
            if theme != "obsidian":
                import re
                recolored = re.sub(r"(?<![-\w])(color\s*:\s*)#ffffff\b",
                                   r"\1#252923", recolored, flags=re.IGNORECASE)
            if recolored != widget.styleSheet():
                widget.setStyleSheet(recolored)
