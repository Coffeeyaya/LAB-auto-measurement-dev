@echo off
REM ---- Change this to your repo folder ----
SET REPO_DIR=C:\Users\ASUS\Desktop\test\LAB-auto-measurement

cd /d "%REPO_DIR%"

echo Fetching latest from origin...
git fetch origin

echo Resetting local changes to match origin/main...
git reset --hard origin/main

echo Cleaning untracked files and folders...
git clean -fd

echo Repository is now synced with Mac version.
pause
