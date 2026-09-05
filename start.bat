@echo off
title MailAccess OSINT Studio
echo ========================================================
echo     Starting MailAccess OSINT Recon Studio Dashboard
echo ========================================================
echo.
pip install -r requirements.txt
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
pause
