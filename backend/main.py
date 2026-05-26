import contextlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
NEXT_STATIC_DIR = STATIC_DIR / "_next"
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "pm.db"))
load_dotenv(BASE_DIR.parent / ".env")

app = FastAPI(title="Project Management Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "PUT", "POST", "OPTIONS"],
    allow_headers=["*"],
)
if NEXT_STATIC_DIR.exists():
    app.mount("/_next", StaticFiles(directory=NEXT_STATIC_DIR), name="next_static")

DEFAULT_BOARD = {
    "columns": [
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {"id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"]},
        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
    ],
    "cards": {
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
        },
    },
}


class Column(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class Card(BaseModel):
    id: str
    title: str
    details: str


class BoardData(BaseModel):
    columns: list[Column]
    cards: dict[str, Card]


def get_db_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with contextlib.closing(get_db_connection()) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                board_json TEXT NOT NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.commit()


@app.on_event("startup")
async def startup() -> None:
    init_db()


def get_index_file() -> Path:
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index file not found")
    return index_file


def get_or_create_user_id(connection: sqlite3.Connection, username: str) -> int:
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row:
        return row["id"]

    cursor.execute("INSERT INTO users (username) VALUES (?)", (username,))
    connection.commit()
    return cursor.lastrowid


def get_board_for_user(connection: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    cursor = connection.cursor()
    cursor.execute("SELECT board_json FROM boards WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        return json.loads(row["board_json"])

    board_json = json.dumps(DEFAULT_BOARD)
    cursor.execute(
        "INSERT INTO boards (user_id, board_json) VALUES (?, ?)",
        (user_id, board_json),
    )
    connection.commit()
    return DEFAULT_BOARD


def save_board_for_user(connection: sqlite3.Connection, user_id: int, board: dict[str, Any]) -> None:
    board_json = json.dumps(board)
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO boards (user_id, board_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            board_json = excluded.board_json,
            updated_at = excluded.updated_at
        """,
        (user_id, board_json),
    )
    connection.commit()


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/hello")
async def hello() -> dict[str, str]:
    return {"message": "hello world"}


@app.get("/api/board", response_model=BoardData)
async def read_board(username: str = Query(..., min_length=1)) -> dict[str, Any]:
    with contextlib.closing(get_db_connection()) as connection:
        user_id = get_or_create_user_id(connection, username)
        return get_board_for_user(connection, user_id)


class AIRequest(BaseModel):
    prompt: str


@app.post("/api/ai")
async def proxy_ai(request: AIRequest) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not configured")

    payload = {
        "model": "openai/gpt-oss-120b:free",
        "messages": [{"role": "user", "content": request.prompt}],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openrouter.ai/v1/chat/completions",
            json=payload,
            headers=headers,
        )

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to call OpenRouter")

    return {"status": "ok", "result": response.json()}


@app.put("/api/board")
async def update_board(
    board: BoardData,
    username: str = Query(..., min_length=1),
) -> dict[str, str]:
    with contextlib.closing(get_db_connection()) as connection:
        user_id = get_or_create_user_id(connection, username)
        save_board_for_user(connection, user_id, board.model_dump())
        return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def root() -> FileResponse:
    return FileResponse(get_index_file())


@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa(full_path: str) -> FileResponse:
    target_file = STATIC_DIR / full_path
    if target_file.exists() and target_file.is_file():
        return FileResponse(target_file)
    return FileResponse(get_index_file())


@app.get("/favicon.ico")
async def favicon() -> FileResponse:
    icon = STATIC_DIR / "favicon.ico"
    if not icon.exists():
        raise HTTPException(status_code=404, detail="Favicon not found")
    return FileResponse(icon)
