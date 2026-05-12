@echo off
chcp 65001 >nul
title GHOST Assistant - Installation
color 0A

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║              👻 GHOST Assistant v1.0 - Setup               ║
echo ║         Windows Voice Assistant (Uzbek / Russian)          ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM ── 1. Python check ──────────────────────────────────────────────
echo [1/6] Python tekshirilmoqda...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ❌ Python topilmadi!
    echo.
    echo  Python 3.11 ni yuklab oling:
    echo  https://www.python.org/downloads/release/python-3119/
    echo.
    echo  O'rnatishda "Add Python to PATH" ni belgilang!
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  ✅ Python %PYVER% topildi

REM ── 2. Virtual environment ────────────────────────────────────────
echo.
echo [2/6] Virtual muhit yaratilmoqda...
if exist "ghost_env\Scripts\activate.bat" (
    echo  ℹ️  ghost_env allaqachon mavjud, o'tkazib yuborildi
) else (
    python -m venv ghost_env
    if %errorlevel% neq 0 (
        echo  ❌ Virtual muhit yaratib bo'lmadi
        pause
        exit /b 1
    )
    echo  ✅ ghost_env yaratildi
)

REM ── 3. Activate ───────────────────────────────────────────────────
echo.
echo [3/6] Virtual muhit yoqilmoqda...
call ghost_env\Scripts\activate.bat
echo  ✅ Yoqildi

REM ── 4. pip upgrade ────────────────────────────────────────────────
echo.
echo [4/6] pip yangilanmoqda...
python -m pip install --upgrade pip setuptools wheel >nul 2>&1
echo  ✅ pip yangilandi

REM ── 5. Dependencies ───────────────────────────────────────────────
echo.
echo [5/6] Kutubxonalar o'rnatilmoqda (bir necha daqiqa ketishi mumkin)...
echo.

if exist "requirements-py311.txt" (
    pip install -r requirements-py311.txt
) else if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    echo  ❌ requirements fayli topilmadi!
    pause
    exit /b 1
)

if %errorlevel% neq 0 (
    echo.
    echo  ❌ O'rnatish xatosi yuz berdi
    echo  Qayta urinib ko'ring yoki requirements.txt ni tekshiring
    pause
    exit /b 1
)

echo.
echo  ✅ Barcha kutubxonalar o'rnatildi

REM ── 6. .env setup ─────────────────────────────────────────────────
echo.
echo [6/6] Konfiguratsiya sozlanmoqda...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo  ✅ .env fayli yaratildi
    ) else (
        echo  ⚠️  .env.example topilmadi, .env qo'lda yarating
    )
) else (
    echo  ℹ️  .env allaqachon mavjud
)

REM ── Done ──────────────────────────────────────────────────────────
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                  ✅ O'rnatish tugadi!                       ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo  Keyingi qadamlar:
echo.
echo  1. .env faylini oching va API kalitlarini kiriting:
echo       PICOVOICE_ACCESS_KEY  - https://console.picovoice.ai/
echo       TELEGRAM_BOT_TOKEN    - @BotFather orqali oling
echo.
echo  2. GHOST ni ishga tushiring:
echo       ghost_env\Scripts\activate.bat
echo       python main.py
echo.
echo  Yoki start.bat ni ishlatishingiz mumkin (avtomatik yaratiladi)
echo.

REM Create start.bat for convenience
echo @echo off > start.bat
echo chcp 65001 ^>nul >> start.bat
echo call ghost_env\Scripts\activate.bat >> start.bat
echo python main.py >> start.bat
echo  ✅ start.bat yaratildi - keyingi safar shu fayl orqali ishga tushiring

echo.
pause
