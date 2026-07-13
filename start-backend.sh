#!/usr/bin/env bash
# Start backend with .env loaded and virtualenv activated
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".env" ]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
else
  echo "Warning: .env not found. Make sure OPENAI_API_KEY and QDRANT settings are exported."
fi

if [ -d ".venv" ]; then
  # shellcheck source=/dev/null
  . .venv/bin/activate
fi

uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
