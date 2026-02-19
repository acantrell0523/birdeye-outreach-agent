@echo off
REM BirdEye Outreach — Claude Desktop Setup
REM Run this once to connect the agent to Claude Desktop, then restart Claude Desktop.

set PYTHON=C:\Users\Austi\AppData\Local\Programs\Python\Python313\python.exe
set PYTHONUTF8=1

echo.
echo  BirdEye Outreach — Claude Desktop Setup
echo  ========================================
echo.

if not exist "%PYTHON%" (
    echo  ERROR: Python not found at expected location.
    echo  Edit this file and update the PYTHON path, or run:
    echo    python setup_claude.py
    echo.
    pause
    exit /b 1
)

"%PYTHON%" setup_claude.py
echo.
pause
