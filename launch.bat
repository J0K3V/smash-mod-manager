@echo off
title Smash Mod Manager v4
cd /d "%~dp0"
python main.py %*
if errorlevel 1 (
    echo.
    echo ERROR: Python not found or crashed.
    echo Make sure Python 3.9+ is installed and in your PATH.
    pause
)
