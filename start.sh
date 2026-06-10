#!/usr/bin/env sh
set -eu

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or is not available on PATH." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is installed but the Docker engine is not running." >&2
  exit 1
fi

cd "$(dirname "$0")"
docker compose up --build --wait

frontend_port="${FRONTEND_PORT:-3000}"
api_port="${API_PORT:-8000}"

echo
echo "DocuExtract is ready:"
echo "  Frontend: http://localhost:${frontend_port}"
echo "  API docs: http://localhost:${api_port}/docs"
