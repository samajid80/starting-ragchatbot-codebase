@echo off
REM Run all quality checks

echo ========================================
echo Running all quality checks...
echo ========================================
echo.

echo [1/4] Checking code formatting...
echo ----------------------------------------
uv run black --check backend/
set BLACK_EXIT=%ERRORLEVEL%

echo.
echo [2/4] Checking import sorting...
echo ----------------------------------------
uv run isort --check-only backend/
set ISORT_EXIT=%ERRORLEVEL%

echo.
echo [3/4] Running linter...
echo ----------------------------------------
uv run flake8 backend/
set FLAKE8_EXIT=%ERRORLEVEL%

echo.
echo [4/4] Running type checker...
echo ----------------------------------------
uv run mypy backend/
set MYPY_EXIT=%ERRORLEVEL%

echo.
echo ========================================
echo Quality Check Summary
echo ========================================

if %BLACK_EXIT% EQU 0 (
    echo [PASS] Black formatting check
) else (
    echo [FAIL] Black formatting check - run 'scripts\format.bat' to fix
)

if %ISORT_EXIT% EQU 0 (
    echo [PASS] Import sorting check
) else (
    echo [FAIL] Import sorting check - run 'scripts\format.bat' to fix
)

if %FLAKE8_EXIT% EQU 0 (
    echo [PASS] Flake8 linting
) else (
    echo [FAIL] Flake8 linting - review errors above
)

if %MYPY_EXIT% EQU 0 (
    echo [PASS] Mypy type checking
) else (
    echo [FAIL] Mypy type checking - review errors above
)

echo ========================================

set /a TOTAL_EXIT=%BLACK_EXIT%+%ISORT_EXIT%+%FLAKE8_EXIT%+%MYPY_EXIT%
if %TOTAL_EXIT% EQU 0 (
    echo.
    echo All checks passed! ✓
    exit /b 0
) else (
    echo.
    echo Some checks failed. Please fix the issues above.
    exit /b 1
)
