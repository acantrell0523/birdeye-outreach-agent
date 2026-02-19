@echo off
REM Run this once to permanently store your Anthropic API key.
REM The key will be available in all future terminal sessions.

echo.
echo  BirdEye Outreach Agent — API Key Setup
echo  ========================================
echo.
echo  You need an Anthropic API key to run the agent.
echo  Get one at: https://console.anthropic.com/
echo.

set /p APIKEY="Paste your API key here (sk-ant-...): "

if "%APIKEY%"=="" (
    echo  No key entered. Exiting.
    exit /b 1
)

REM Set permanently for the current user (survives restarts)
setx ANTHROPIC_API_KEY "%APIKEY%"

echo.
echo  Key saved. You can now run the agent with:
echo    run.bat sample\contacts.csv
echo.
echo  NOTE: Open a NEW terminal window for the key to take effect.
echo.
pause
