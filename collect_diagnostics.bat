@echo off
title FlowPilot System Diagnostic Collector
color 0A
echo ======================================================================
echo             FLOWPILOT AUTOMATED DIAGNOSTIC COLLECTOR
echo ======================================================================
echo.
echo Running diagnostic suite to test microphone capture, audio hardware,
echo Win32 global hotkeys, and local faster-whisper CTranslate2 STT...
echo.

python diagnose.py

echo.
echo ======================================================================
echo If you encountered an issue, attach the generated file:
echo "flowpilot_diagnostic_report.txt"
echo to your bug report or email it to support@flowpilot.local.
echo ======================================================================
echo.
pause
