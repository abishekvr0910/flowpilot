@echo off
title FlowPilot Voice Intelligence
cd /d "%~dp0"
echo ============================================================
echo   FLOWPILOT - Universal Multilingual Voice Intelligence
echo ============================================================
echo   [*] Starting Native Desktop App (HUD + System Tray)...
echo   [*] Hotkeys: 'Ctrl + Shift + Space', 'Ctrl + Alt + Space', 'F9'
echo ============================================================
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" desktop_app.py
) else (
    python desktop_app.py
)
pause
