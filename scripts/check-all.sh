#!/bin/bash
# Run all quality checks

echo "========================================"
echo "Running all quality checks..."
echo "========================================"
echo ""

echo "[1/4] Checking code formatting..."
echo "----------------------------------------"
uv run black --check backend/
BLACK_EXIT=$?

echo ""
echo "[2/4] Checking import sorting..."
echo "----------------------------------------"
uv run isort --check-only backend/
ISORT_EXIT=$?

echo ""
echo "[3/4] Running linter..."
echo "----------------------------------------"
uv run flake8 backend/
FLAKE8_EXIT=$?

echo ""
echo "[4/4] Running type checker..."
echo "----------------------------------------"
uv run mypy backend/
MYPY_EXIT=$?

echo ""
echo "========================================"
echo "Quality Check Summary"
echo "========================================"

if [ $BLACK_EXIT -eq 0 ]; then
    echo "[PASS] Black formatting check"
else
    echo "[FAIL] Black formatting check - run 'scripts/format.sh' to fix"
fi

if [ $ISORT_EXIT -eq 0 ]; then
    echo "[PASS] Import sorting check"
else
    echo "[FAIL] Import sorting check - run 'scripts/format.sh' to fix"
fi

if [ $FLAKE8_EXIT -eq 0 ]; then
    echo "[PASS] Flake8 linting"
else
    echo "[FAIL] Flake8 linting - review errors above"
fi

if [ $MYPY_EXIT -eq 0 ]; then
    echo "[PASS] Mypy type checking"
else
    echo "[FAIL] Mypy type checking - review errors above"
fi

echo "========================================"

TOTAL_EXIT=$((BLACK_EXIT + ISORT_EXIT + FLAKE8_EXIT + MYPY_EXIT))
if [ $TOTAL_EXIT -eq 0 ]; then
    echo ""
    echo "All checks passed! ✓"
    exit 0
else
    echo ""
    echo "Some checks failed. Please fix the issues above."
    exit 1
fi
