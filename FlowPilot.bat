@echo off
title FlowPilot Voice Intelligence
cd /d "%~dp0"

echo ============================================================
echo   FLOWPILOT - Desktop Voice Intelligence
echo ============================================================
echo   [*] Starting FlowPilot Companion...
echo   [*] Look for the companion on your screen or the System Tray!
echo   [*] Hotkeys: Ctrl+Shift+Space, F9 (Push-to-Talk)
echo ============================================================

if exist "%~dp0.venv\Scripts\python.exe" (
    start "" "%~dp0.venv\Scripts\python.exe" desktop_app.py
) else if exist "%LOCALAPPDATA%\Programs\FlowPilot\FlowPilot.exe" (
    echo   [*] Launching installed FlowPilot desktop application...
    start "" "%LOCALAPPDATA%\Programs\FlowPilot\FlowPilot.exe"
) else if exist "%~dp0releases\FlowPilot-Setup-v3.1.3.exe" (
    echo   [*] Local Python venv not found. Launching FlowPilot 1-Click Setup...
    start "" "%~dp0releases\FlowPilot-Setup-v3.1.3.exe"
) else (
    start "" python desktop_app.py
)
