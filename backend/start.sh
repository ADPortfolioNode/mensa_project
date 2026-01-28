#!/bin/sh
set -e

echo "🔍 Checking Pydantic Version..."
python -c "import pydantic; print(f'Pydantic Version: {pydantic.VERSION}')"

echo "🚀 Starting Backend (uvicorn on :5000)..."
# Run the FastAPI app with uvicorn; keep container alive if it crashes for inspection
uvicorn main:app --host 0.0.0.0 --port 5000 || {
    echo "❌ App crashed. Keeping container alive for debugging..."
    tail -f /dev/null
}