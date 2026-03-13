@echo off
REM ============================================================
REM AI Research Assistant — Windows 10 Setup Script
REM Run this from the root of the project folder
REM ============================================================

echo.
echo ============================================================
echo  AI Research Assistant — Windows 10 Setup
echo ============================================================
echo.

REM ── Check Python ─────────────────────────────────────────────
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python not found. Install Python 3.11 from python.org
    echo         Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
echo [OK] Python found.

REM ── Check Node ───────────────────────────────────────────────
node --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Node.js not found. Install Node 18 LTS from nodejs.org
    pause
    exit /b 1
)
echo [OK] Node.js found.

REM ── Check Ollama ─────────────────────────────────────────────
ollama --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [WARNING] Ollama not found. Download from: https://ollama.com/download/windows
    echo           After installing, re-run this script.
    pause
    exit /b 1
)
echo [OK] Ollama found.

REM ── Pull Ollama Models ────────────────────────────────────────
echo.
echo Pulling Ollama models (this may take a few minutes on first run)...
ollama pull phi3
ollama pull nomic-embed-text
echo [OK] Models ready.

REM ── Backend Setup ────────────────────────────────────────────
echo.
echo Setting up Backend...
cd Backend

IF NOT EXIST venv (
    python -m venv venv
    echo [OK] Virtual environment created.
)

call venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo [OK] Backend dependencies installed.

REM Create .env from template if not exists
IF NOT EXIST .env (
    copy .env.example .env
    echo [OK] .env created from template.
    echo [ACTION REQUIRED] Open Backend\.env and replace SECRET_KEY with a real secret!
)

cd ..

REM ── Frontend Setup ───────────────────────────────────────────
echo.
echo Setting up Frontend...
cd frontend
npm install --silent
echo [OK] Frontend dependencies installed.
cd ..

REM ── Done ─────────────────────────────────────────────────────
echo.
echo ============================================================
echo  Setup complete!
echo ============================================================
echo.
echo  To start the app:
echo.
echo  1. In one terminal (start Ollama):
echo     ollama serve
echo.
echo  2. In a second terminal (start backend):
echo     cd Backend
echo     venv\Scripts\activate
echo     uvicorn main:app --reload --port 8000
echo.
echo  3. In a third terminal (start frontend):
echo     cd frontend
echo     npm start
echo.
echo  Then open: http://localhost:3000
echo ============================================================
pause
