# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A single-board Kanban web app (MVP) with an AI chat sidebar. The backend serves the Next.js static build and exposes a REST API. Everything runs in Docker.

- **Frontend**: Next.js 16 (app router), Tailwind CSS v4, `@dnd-kit` for drag-and-drop
- **Backend**: Python FastAPI, Uvicorn, SQLite via `sqlite3`, OpenRouter for AI
- **Auth**: hardcoded `user` / `password` — no real auth, no sessions
- **AI model**: `openai/gpt-oss-120b:free` via OpenRouter (`OPENROUTER_API_KEY` in `.env`)

## Commands

### Frontend (`frontend/`)

```
npm run dev          # dev server on :3000
npm run build        # static export consumed by Dockerfile
npm run test:unit    # vitest (unit tests)
npm run test:e2e     # playwright (E2E tests)
npm run lint         # eslint
```

Run a single vitest test file:
```
npx vitest run src/lib/kanban.test.ts
```

### Backend (`backend/`)

```
# From repo root — loads .env automatically
uvicorn backend.main:app --reload --port 8000

# Run backend tests
cd backend && python -m pytest test_main.py
# or
cd backend && python -m unittest test_main.py
```

### Docker (full stack)

```
scripts/start.ps1   # Windows — builds frontend, builds Docker image, starts container on :8000
scripts/start.sh    # Mac/Linux
scripts/stop.ps1    # Windows
scripts/stop.sh     # Mac/Linux
```

Manual equivalent:
```
cd frontend && npm install && npm run build
docker build -t pm-app .
docker run --rm -d -p 8000:8000 --name pm-app-container pm-app
```

## Architecture

### Data flow

The frontend (`KanbanBoard.tsx`) owns in-memory board state. Every mutation (drag, rename, add/delete card) calls `updateBoard()`, which updates React state and immediately fires `PUT /api/board?username=<user>` in the background. On mount, it fetches `GET /api/board?username=<user>` to load persisted state.

The AI sidebar (`ChatSidebar.tsx`) posts to `POST /api/ai?username=<user>` with the current board and the user's prompt. If the response contains `updatedBoard`, the frontend calls `onUpdateBoard()` to replace board state, which also triggers a save.

### Board data model

Defined in `frontend/src/lib/kanban.ts` and mirrored as Pydantic models in `backend/main.py`:

```
BoardData { columns: Column[], cards: Record<id, Card> }
Column    { id, title, cardIds: string[] }
Card      { id, title, details }
```

Board state is stored in SQLite as a single JSON blob in `boards.board_json` (one row per user, upserted on every write).

### Backend (`backend/main.py`)

Single-file FastAPI app. Key API routes:
- `GET /api/board?username=` — returns board JSON, creates default board on first access
- `PUT /api/board?username=` — upserts board JSON for user
- `POST /api/ai?username=` — proxies prompt + board to OpenRouter; parses structured JSON from AI response; if `updatedBoard` is present and valid, persists it and returns it to the frontend
- `GET /` and `GET /{full_path}` — serves built Next.js static files from `backend/static/`

The AI system prompt instructs the model to return `{ response, updatedBoard? }`. `parse_structured_ai_response()` extracts the first JSON object from the raw AI output (handles markdown-wrapped JSON).

### Frontend dev vs production API

`KanbanBoard.tsx` uses `API_BASE = "http://localhost:8000/api"` in dev mode and `"/api"` in production (served by FastAPI).

### Docker build

The Dockerfile copies the pre-built Next.js output from `frontend/.next/server/app/index.html` and `frontend/.next/static/` into `backend/static/`. The backend then serves these as static files.

## Color scheme

CSS variables defined in `globals.css`:
- `--accent-yellow`: `#ecad0a`
- `--primary-blue`: `#209dd7`
- `--secondary-purple`: `#753991`
- `--navy-dark`: `#032147`
- `--gray-text`: `#888888`

## Coding standards

- No over-engineering; no unnecessary defensive programming; no extra features
- No emojis anywhere in code, UI, or documentation
- Identify root cause before attempting a fix — prove with evidence
- Keep it simple and concise
