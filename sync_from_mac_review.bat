@echo off

echo Fetching latest from origin...
git fetch origin

echo Resetting local changes to match origin/review...
git reset --hard origin/review

echo Cleaning untracked files and folders...
git clean -fd

echo Repository is now synced with Mac version.
pause
