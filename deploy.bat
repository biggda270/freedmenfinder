@echo off
REM Quick deployment script for FREEDMENFINDER
REM This script helps push your code to GitHub

echo.
echo =====================================================
echo FREEDMENFINDER Deployment Script
echo =====================================================
echo.

echo Step 1: Verify git is initialized
git status
if %ERRORLEVEL% NEQ 0 (
    echo Git not initialized. Run: git init
    exit /b 1
)

echo.
echo Step 2: Check for uncommitted changes
git status --short
if %ERRORLEVEL% NEQ 0 (
    echo Error checking git status
    exit /b 1
)

echo.
echo Step 3: Instructions for GitHub deployment
echo.
echo To deploy to GitHub:
echo.
echo 1. Create a repository at: https://github.com/new
echo    - Name: freedmenfinder
echo    - Visibility: Public
echo    - Do NOT initialize with README or .gitignore
echo.
echo 2. Copy your GitHub repository URL (HTTPS)
echo.
echo 3. Run the command below (replace YOUR_USERNAME):
echo.
echo    git remote add origin https://github.com/YOUR_USERNAME/freedmenfinder.git
echo    git branch -M main
echo    git push -u origin main
echo.
echo 4. Then go to https://share.streamlit.io to deploy
echo.
echo =====================================================
echo Git info:
git remote -v
git log --oneline -5
echo =====================================================
echo.
echo For detailed instructions, see DEPLOYMENT.md
echo.
pause
