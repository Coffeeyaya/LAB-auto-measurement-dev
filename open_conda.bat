@echo off
REM Open cmd in the current folder with Anaconda base environment activated

REM Change directory to the folder where the BAT file is located
cd /d %~dp0

REM Call conda to activate the base environment
call "C:\\Users\\Snow\\anaconda3\\condabin\\conda.bat" activate base

REM Keep the terminal open
cmd

