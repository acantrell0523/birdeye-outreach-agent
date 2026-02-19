@echo off
REM BirdEye LinkedIn Outreach Agent — Quick Launcher
REM Usage: run.bat contacts.csv
REM        run.bat contacts.csv 10

set PYTHON=C:\Users\Austi\AppData\Local\Programs\Python\Python313\python.exe
set PYTHONUTF8=1

if "%1"=="" (
    echo.
    echo  BirdEye LinkedIn Outreach Agent
    echo  ================================
    echo  Usage: run.bat ^<csv_file^> [limit]
    echo.
    echo  Accepts TWO input formats:
    echo    1. Account/company list  ^(Sales Navigator account export^)
    echo       Agent finds the right contact at each company automatically.
    echo.
    echo    2. Contacts list  ^(Sales Navigator people export^)
    echo       Agent researches and drafts for pre-identified contacts.
    echo.
    echo  Examples:
    echo    run.bat "C:\Users\Austi\Downloads\my_accounts.csv"
    echo    run.bat "C:\Users\Austi\Downloads\my_accounts.csv" 10
    echo    run.bat sample\contacts.csv 2
    echo.
    exit /b 1
)

if "%ANTHROPIC_API_KEY%"=="" (
    echo.
    echo  ERROR: ANTHROPIC_API_KEY is not set.
    echo  Run setup_key.bat first to configure it.
    echo.
    exit /b 1
)

"%PYTHON%" agent.py %*
