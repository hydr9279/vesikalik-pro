@echo off
cd /d "%~dp0"
if not exist .venv ( echo Once kurulum.bat calistirilmali. & pause & exit /b 1 )
start "" .venv\Scripts\pythonw.exe app.py
