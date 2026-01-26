#!/bin/sh
set -e

echo "🔍 Checking Pydantic Version..."
python -c "import pydantic; print(f'Pydantic Version: {pydantic.VERSION}')"

echo "🚀 Starting Backend..."
# Run the app; if it crashes, keep container alive for debugging
python main.py || {
    echo "❌ App crashed. Keeping container alive for debugging..."
    tail -f /dev/null
}