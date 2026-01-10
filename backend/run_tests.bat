@echo off
REM Quick test runner script for Windows
echo Running SlotFit Backend Tests...
echo.

python -m pytest tests/ -v --tb=short

pause
