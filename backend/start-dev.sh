#!/usr/bin/env bash
# Start-dev helper for local backend development. Loads backend/.env and runs uvicorn.
set -euo pipefail
# If a .env file exists, load it
ENV_FILE="$(pwd)/backend/.env"
if [ -f "$ENV_FILE" ]; then
  echo "Loading env from $ENV_FILE"
  set -o allexport
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +o allexport
fi

# Activate virtualenv if it exists
if [ -f "./.venv/bin/activate" ]; then
  echo "Activating venv"
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Set defaults if not provided
: "${GEMINI_MODEL:=models/gemini-2.5-flash}"
: "${GEMINI_API_KEY:=}"

echo "Starting uvicorn with GEMINI_API_KEY=${GEMINI_API_KEY:+(set)} GEMINI_MODEL=${GEMINI_MODEL}"

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
