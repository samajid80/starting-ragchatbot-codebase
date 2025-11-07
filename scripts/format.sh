#!/bin/bash
# Format code with black and isort

echo "Running black..."
uv run black backend/

echo ""
echo "Running isort..."
uv run isort backend/

echo ""
echo "Code formatting complete!"
