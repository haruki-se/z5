@echo off
chcp 65001 > nul
cd /d "%~dp0"
python -m pip install flask python-dotenv requests qrcode
python web_app.py
pause
