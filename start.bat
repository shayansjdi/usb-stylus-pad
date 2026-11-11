@echo off
setlocal
title USB Stylus Pad (Galam Noori) - Pen and Mouse Server

cd /d "%~dp0pc_server"

where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python not found on your system!
        echo Please install Python and check "Add Python to PATH".
        echo.
        pause
        exit /b 1
    ) else (
        set PYCMD=py
    )
) else (
    set PYCMD=python
)

echo Starting Galam Noori Server...
%PYCMD% server.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] An error occurred while running the server.
    pause
)
