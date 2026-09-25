@echo off
cd /d "%~dp0backend"
if not exist venv (
  py -m venv venv
)
call venv\Scripts\activate
python -m pip install -r requirements.txt
echo.
echo Starting FinGuard AI...
echo Open http://127.0.0.1:8000
echo Press CTRL+C to stop.
python main.py
pause
