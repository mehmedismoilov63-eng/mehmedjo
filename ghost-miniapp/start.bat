@echo off
chcp 65001 >nul
title GHOST Claude Bridge

echo.
echo  👻 GHOST Claude Bridge ishga tushmoqda...
echo.

cd /d "%~dp0"

REM Virtual env tekshirish
if exist "..\ghost_env\Scripts\activate.bat" (
    call ..\ghost_env\Scripts\activate.bat
)

REM Lokal brauzerda test qilish uchun Telegram auth o'chiriladi.
if "%GHOST_REQUIRE_TELEGRAM_AUTH%"=="" set GHOST_REQUIRE_TELEGRAM_AUTH=false

REM Backend
echo  [1/2] Backend: http://localhost:8000
start "GHOST Backend" cmd /k "cd /d "%~dp0backend" && python main.py"

timeout /t 2 /nobreak >nul

REM Agent
echo  [2/2] Local Agent ishga tushmoqda...
start "GHOST Agent" cmd /k "cd /d "%~dp0backend" && python agent.py"

echo.
echo  ✅ Tayyor! Brauzerda oching: http://localhost:8000
echo.
pause
