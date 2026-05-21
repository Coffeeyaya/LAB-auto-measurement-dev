@echo off
cd /d %~dp0
start cmd /k "call C:\Users\Snow\anaconda3\condabin\conda.bat activate base && python laser_control.py"