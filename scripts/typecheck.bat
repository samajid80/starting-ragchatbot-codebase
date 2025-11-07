@echo off
REM Run type checking with mypy

echo Running mypy...
uv run mypy backend/

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Type checking passed!
) else (
    echo.
    echo Type checking found issues. Please review above.
    exit /b 1
)
