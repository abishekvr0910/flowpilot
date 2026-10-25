"""Feature 32: Inspect Windows process integrity before text injection."""

import logging
import os
import sys
from typing import Optional

logger = logging.getLogger("FlowPilot.WindowsIntegrity")


def target_has_higher_integrity(hwnd: int) -> Optional[bool]:
    """Return True for a higher-integrity target, None if inspection fails."""
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        import win32api
        import win32con
        import win32process
        import win32security

        _, target_pid = win32process.GetWindowThreadProcessId(hwnd)
        if target_pid == os.getpid():
            return False

        def token_rid(process_handle) -> int:
            token = win32security.OpenProcessToken(process_handle, win32con.TOKEN_QUERY)
            try:
                sid, _ = win32security.GetTokenInformation(
                    token, win32security.TokenIntegrityLevel,
                )
                return sid.GetSubAuthority(sid.GetSubAuthorityCount() - 1)
            finally:
                token.Close()

        own_rid = token_rid(win32api.GetCurrentProcess())
        target_process = win32api.OpenProcess(0x1000, False, target_pid)
        try:
            target_rid = token_rid(target_process)
        finally:
            target_process.Close()
        return target_rid > own_rid
    except Exception as exc:
        logger.warning("Could not inspect target integrity level: %s", exc)
        return None
