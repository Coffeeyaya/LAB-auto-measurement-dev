@echo off

REM Start measurement script
start "Measurement" cmd /k python keithley.py

REM Small delay to ensure file is created
timeout /t 2 >nul

REM Start live plot script
start "Live Plot" cmd /k python plot.py
