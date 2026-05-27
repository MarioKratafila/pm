#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Building Docker image..."
docker build -t pm-app .

echo "Starting container..."
docker run --rm -d -p 8000:8000 --name pm-app-container pm-app

echo "Application should be available at http://localhost:8000"
