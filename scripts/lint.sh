#!/bin/bash
# Run linting checks

echo "Running flake8..."
uv run flake8 backend/

if [ $? -eq 0 ]; then
    echo ""
    echo "Linting passed!"
else
    echo ""
    echo "Linting failed. Please fix the issues above."
    exit 1
fi
