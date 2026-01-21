@echo off
echo ========================================
echo SlotFit Development Servers
echo ========================================
echo.

echo [1/4] Killing stale Python/Uvicorn processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM uvicorn.exe 2>nul
echo      Done (ignore "not found" errors)
echo.

echo [2/4] Starting backend server...
cd /d "%~dp0backend"
if exist "venv\Scripts\activate.bat" (
    start "SlotFit Backend" cmd /k "call venv\Scripts\activate.bat && echo Backend starting on http://localhost:8000/docs && echo Press Ctrl+C to stop && uvicorn app.main:app --reload --port 8000"
) else if exist ".venv\Scripts\activate.bat" (
    start "SlotFit Backend" cmd /k "call .venv\Scripts\activate.bat && echo Backend starting on http://localhost:8000/docs && echo Press Ctrl+C to stop && uvicorn app.main:app --reload --port 8000"
) else (
    echo ERROR: Virtual environment not found. Expected venv or .venv in backend directory.
    pause
    exit /b 1
)
echo      Backend window opened
echo.

echo [3/4] Starting frontend server...
cd /d "%~dp0web"
start "SlotFit Frontend" cmd /k "echo Frontend starting on http://localhost:5173 && echo Press Ctrl+C to stop && npm run dev"
echo      Frontend window opened
echo.

echo [4/4] Both servers starting...
echo.
echo ========================================
echo Backend:  http://localhost:8000/docs
echo Frontend: http://localhost:5173
echo ========================================
echo.
echo Both servers are running in separate windows.
echo Close those windows to stop the servers.
echo.
pause
