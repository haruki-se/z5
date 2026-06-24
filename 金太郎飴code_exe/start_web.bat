@echo off
chcp 65001 > nul
cd /d "%~dp0"
pip install --quiet flask qrcode
python web_app.py
pause
