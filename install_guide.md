# GHOST Assistant Installation Guide

## 🚨 Installation Issues & Solutions

### Problem: Python 3.13 Compatibility
Python 3.13 has compatibility issues with some packages. Here are solutions:

## Solution 1: Use Python 3.11 (Recommended)

1. **Install Python 3.11**
   - Download from: https://www.python.org/downloads/release/python-3119/
   - Choose Windows installer (64-bit)
   - Add to PATH during installation

2. **Verify Python version**
   ```cmd
   python --version
   # Should show: Python 3.11.x
   ```

3. **Install dependencies**
   ```cmd
   pip install -r requirements-py311.txt
   ```

## Solution 2: Try with Python 3.13 (Limited)

1. **Install core packages first**
   ```cmd
   pip install faster-whisper vosk SpeechRecognition pvporcupine
   ```

2. **Install GUI packages**
   ```cmd
   pip install PyQt6==6.5.0 PyQt6-tools==6.5.0
   ```

3. **Install system packages**
   ```cmd
   pip install pycaw screen-brightness-control pyautogui psutil pygetwindow comtypes
   ```

4. **Install remaining packages**
   ```cmd
   pip install edge-tts pyttsx3 rapidfuzz python-telegram-bot APScheduler googlesearch-python requests deep-translator librosa scikit-learn python-dotenv
   ```

## Solution 3: Manual Package Installation

### PyAudio Installation
Download pre-compiled wheel:
- Python 3.11: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
- Python 3.13: https://github.com/mhammond/pyaudio/releases

Install with:
```cmd
pip install path/to/downloaded/pyaudio.whl
```

### Alternative Audio Libraries
If PyAudio fails, try:
```cmd
pip install sounddevice simpleaudio
```

## 🛠️ Development Environment Setup

### 1. Create Virtual Environment (Recommended)
```cmd
python -m venv ghost_env
ghost_env\Scripts\activate
```

### 2. Install Dependencies
```cmd
pip install --upgrade pip setuptools wheel
pip install -r requirements-py311.txt
```

### 3. Configure Environment
```cmd
copy .env.example .env
# Edit .env with your API keys
```

### 4. Run GHOST
```cmd
python main.py
```

## 🔧 Troubleshooting

### Common Issues:

1. **"No module named 'distutils.msvccompiler'"**
   - Solution: Use Python 3.11 or install Visual Studio Build Tools

2. **PyQt6 build errors**
   - Solution: Use Python 3.11 or install specific PyQt6 version

3. **PyAudio installation fails**
   - Solution: Download pre-compiled wheel file

4. **"qmake not found"**
   - Solution: Install Qt or use pre-compiled PyQt6

### Visual Studio Build Tools
If you want to compile from source:
1. Download Visual Studio Build Tools
2. Install "C++ build tools"
3. Add to PATH

## 📦 Quick Start Script

Create `install.bat`:
```batch
@echo off
echo Installing GHOST Assistant...

REM Check Python version
python --version | findstr "3.11" >nul
if %errorlevel% neq 0 (
    echo ERROR: Python 3.11 required
    echo Please install Python 3.11 from: https://www.python.org/downloads/release/python-3119/
    pause
    exit /b 1
)

REM Create virtual environment
python -m venv ghost_env
call ghost_env\Scripts\activate.bat

REM Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements-py311.txt

REM Configure environment
copy .env.example .env

echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Edit .env with your API keys
echo 2. Run: python main.py
echo.
pause
```

## 🎯 Recommended Setup

For best experience, use:
- **Python 3.11.9** (stable and compatible)
- **Windows 10/11** (64-bit)
- **Visual Studio Code** (for development)
- **Git** (for version control)

## 📞 Support

If you still have issues:
1. Check Python version: `python --version`
2. Update pip: `python -m pip install --upgrade pip`
3. Try virtual environment
4. Contact support with error details

---

**Remember:** Python 3.11 is recommended for best compatibility!
