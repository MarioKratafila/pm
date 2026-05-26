 # Backend Agent Guide

## Purpose
This file describes the backend scaffolding and the intended responsibilities for the Python FastAPI service.

## Current backend state
- Directory: `backend/`
- Framework: FastAPI
- Server: Uvicorn via `uv run`
- Static content: served from `backend/static`
- API: simple health and hello endpoints
- Config: `backend/pyproject.toml` manages dependencies

## Entry point
- `backend/main.py` defines the FastAPI app and static serving.
- `app.mount("/static", ...)` exposes static assets under `/static`.
- `GET /` returns `backend/static/index.html`.

## API endpoints
- `GET /api/health` — returns `{ status: "ok" }`
- `GET /api/hello` — returns `{ message: "hello world" }`

## Next work
- Add user authentication and session support.
- Add board and card persistence endpoints.
- Integrate the frontend build into static serving.
- Configure SQLite persistence and `OPENROUTER_API_KEY` support.