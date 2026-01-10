@echo off
echo ========================================
echo SlotFit Backend Server Restart
echo ========================================
echo.

echo [1/3] Killing stale Python/Uvicorn processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM uvicorn.exe 2>nul
echo      Done (ignore "not found" errors)
echo.

echo [2/3] Changing to backend directory...
cd /d "%~dp0backend"
echo      Now in: %cd%
echo.

echo [3/3] Activating venv and starting FastAPI server...
echo      Swagger UI: http://localhost:8000/docs
echo      Press Ctrl+C to stop
echo ========================================
echo.

call .venv\Scripts\activate.bat
uvicorn app.main:app --reload --port 8000
