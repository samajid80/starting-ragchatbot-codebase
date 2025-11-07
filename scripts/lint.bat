@echo off
REM Run linting checks

echo Running flake8...
uv run flake8 backend/

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Linting passed!
) else (
    echo.
    echo Linting failed. Please fix the issues above.
    exit /b 1
)
