@echo off
title Lutum Veritas Backend
cd /d "%~dp0lutum-backend"
echo === Lutum Veritas Backend ===
echo.
echo NOTE: Hot reload disabled wegen Windows asyncio/subprocess Bug
echo Bei Code-Aenderungen: Ctrl+C und neu starten
echo.
"C:\Users\hacka\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8420
pause
