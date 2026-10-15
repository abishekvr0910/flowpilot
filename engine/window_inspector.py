import sys
from typing import Dict, Any, Optional

try:
    import win32gui
    import win32process
    import psutil
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class WindowInspector:
    """
    Safely inspects the active foreground application using Win32 API.
    Zero screenshots taken. 100% private and enterprise-compliant.
    """

    APP_CATEGORY_MAP = {
        "code.exe": "developer",
        "cursor.exe": "developer",
        "devenv.exe": "developer",
        "pycharm64.exe": "developer",
        "idea64.exe": "developer",
        "sublime_text.exe": "developer",
        "windowsterminal.exe": "terminal",
        "cmd.exe": "terminal",
        "powershell.exe": "terminal",
        "bash.exe": "terminal",
        "wsl.exe": "terminal",
        "alacritty.exe": "terminal",
        "wezterm-gui.exe": "terminal",
        "mintty.exe": "terminal",
        "slack.exe": "chat",
        "teams.exe": "chat",
        "discord.exe": "chat",
        "telegram.exe": "chat",
        "whatsapp.exe": "chat",
        "chrome.exe": "browser",
        "msedge.exe": "browser",
        "firefox.exe": "browser",
        "brave.exe": "browser",
        "outlook.exe": "email",
        "thunderbird.exe": "email",
        "winword.exe": "document",
        "notepad.exe": "document",
        "notepad++.exe": "developer",
        "obsidian.exe": "notes",
        "notion.exe": "notes"
    }

    @classmethod
    def get_active_window_info(cls) -> Dict[str, Any]:
        info = {
            "hwnd": 0,
            "title": "",
            "process_name": "unknown",
            "category": "general"
        }

        if not HAS_WIN32 or sys.platform != "win32":
            return info

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return info

            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            process_name = "unknown"
            try:
                proc = psutil.Process(pid)
                process_name = proc.name().lower()
            except Exception:
                pass

            category = cls.APP_CATEGORY_MAP.get(process_name, "general")

            return {
                "hwnd": hwnd,
                "title": title,
                "process_name": process_name,
                "category": category
            }
        except Exception as e:
            print(f"[WindowInspector Error] {e}")
            return info
