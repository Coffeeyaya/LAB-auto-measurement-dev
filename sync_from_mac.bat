@echo off

echo Fetching latest from origin...
git fetch origin

echo Resetting local changes to match origin/main...
git reset --hard origin/main

echo Cleaning untracked files and folders...
git clean -fd

echo Repository is now synced with Mac version.
pause
