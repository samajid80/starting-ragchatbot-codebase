#!/bin/bash
# Run type checking with mypy

echo "Running mypy..."
uv run mypy backend/

if [ $? -eq 0 ]; then
    echo ""
    echo "Type checking passed!"
else
    echo ""
    echo "Type checking found issues. Please review above."
    exit 1
fi
