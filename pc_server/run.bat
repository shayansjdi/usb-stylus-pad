@echo off
setlocal
cd /d "%~dp0"
python server.py
if %errorlevel% neq 0 pause
