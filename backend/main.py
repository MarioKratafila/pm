import contextlib
import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
NEXT_STATIC_DIR = STATIC_DIR / "_next"
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "pm.db"))
load_dotenv(BASE_DIR.parent / ".env")

_sessions: dict[str, str] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Project Management Backend", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "PUT", "POST", "DELETE", "PATCH", "OPTIONS"],
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


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class CreateBoardRequest(BaseModel):
    name: str


class RenameBoardRequest(BaseModel):
    name: str


class AIRequest(BaseModel):
    prompt: str
    board: BoardData | None = None
    board_id: int | None = None


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt.hex() + ":" + dk.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, dk_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return secrets.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


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
                password_hash TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute("PRAGMA table_info(users)")
        user_cols = {row[1] for row in cursor.fetchall()}
        if "password_hash" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='boards'")
        boards_exists = cursor.fetchone() is not None

        if boards_exists:
            cursor.execute("PRAGMA table_info(boards)")
            board_cols = {row[1] for row in cursor.fetchall()}
            if "name" not in board_cols:
                cursor.execute(
                    "ALTER TABLE boards ADD COLUMN name TEXT NOT NULL DEFAULT 'My Board'"
                )
                cursor.execute(
                    """
                    CREATE TABLE boards_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        name TEXT NOT NULL DEFAULT 'My Board',
                        board_json TEXT NOT NULL,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                    """
                )
                cursor.execute(
                    "INSERT INTO boards_new SELECT id, user_id, name, board_json, updated_at FROM boards"
                )
                cursor.execute("DROP TABLE boards")
                cursor.execute("ALTER TABLE boards_new RENAME TO boards")
        else:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS boards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL DEFAULT 'My Board',
                    board_json TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )

        connection.commit()


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


def get_user_by_username(connection: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    return cursor.fetchone()


def create_user_with_password(connection: sqlite3.Connection, username: str, password: str) -> int:
    password_hash = hash_password(password)
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, password_hash),
    )
    connection.commit()
    return cursor.lastrowid


def get_boards_for_user(connection: sqlite3.Connection, user_id: int) -> list[dict[str, Any]]:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, name, updated_at, board_json FROM boards WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    result = []
    for row in rows:
        board_data = json.loads(row["board_json"])
        card_count = sum(len(col.get("cardIds", [])) for col in board_data.get("columns", []))
        result.append(
            {
                "id": row["id"],
                "name": row["name"],
                "updated_at": row["updated_at"],
                "card_count": card_count,
            }
        )
    return result


def get_board_by_id(
    connection: sqlite3.Connection, board_id: int, user_id: int
) -> dict[str, Any] | None:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT board_json FROM boards WHERE id = ? AND user_id = ?",
        (board_id, user_id),
    )
    row = cursor.fetchone()
    return json.loads(row["board_json"]) if row else None


def get_or_create_default_board(
    connection: sqlite3.Connection, user_id: int
) -> tuple[int, dict[str, Any]]:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, board_json FROM boards WHERE user_id = ? ORDER BY id ASC LIMIT 1",
        (user_id,),
    )
    row = cursor.fetchone()
    if row:
        return row["id"], json.loads(row["board_json"])

    board_json = json.dumps(DEFAULT_BOARD)
    cursor.execute(
        "INSERT INTO boards (user_id, name, board_json) VALUES (?, ?, ?)",
        (user_id, "My Board", board_json),
    )
    connection.commit()
    return cursor.lastrowid, DEFAULT_BOARD


def create_board_for_user(
    connection: sqlite3.Connection, user_id: int, name: str
) -> int:
    board_json = json.dumps(DEFAULT_BOARD)
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO boards (user_id, name, board_json) VALUES (?, ?, ?)",
        (user_id, name, board_json),
    )
    connection.commit()
    return cursor.lastrowid


def save_board_by_id(
    connection: sqlite3.Connection, board_id: int, user_id: int, board: dict[str, Any]
) -> bool:
    board_json = json.dumps(board)
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE boards SET board_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
        (board_json, board_id, user_id),
    )
    connection.commit()
    return cursor.rowcount > 0


def delete_board_by_id(connection: sqlite3.Connection, board_id: int, user_id: int) -> bool:
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM boards WHERE user_id = ?", (user_id,))
    if cursor.fetchone()["cnt"] <= 1:
        return False
    cursor.execute("DELETE FROM boards WHERE id = ? AND user_id = ?", (board_id, user_id))
    connection.commit()
    return cursor.rowcount > 0


def rename_board_by_id(
    connection: sqlite3.Connection, board_id: int, user_id: int, name: str
) -> bool:
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE boards SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
        (name, board_id, user_id),
    )
    connection.commit()
    return cursor.rowcount > 0


def get_current_user(authorization: str | None = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]
    username = _sessions.get(token)
    if not username:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return username


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/hello")
async def hello() -> dict[str, str]:
    return {"message": "hello world"}


@app.post("/api/register")
async def register(request: RegisterRequest) -> dict[str, str]:
    if len(request.username) < 3 or len(request.username) > 32:
        raise HTTPException(status_code=400, detail="Username must be 3–32 characters")
    if not request.username.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Username may only contain letters, digits, hyphens, and underscores")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    with contextlib.closing(get_db_connection()) as connection:
        existing = get_user_by_username(connection, request.username)
        if existing:
            raise HTTPException(status_code=409, detail="Username already taken")

        user_id = create_user_with_password(connection, request.username, request.password)
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO boards (user_id, name, board_json) VALUES (?, ?, ?)",
            (user_id, "My Board", json.dumps(DEFAULT_BOARD)),
        )
        connection.commit()

    token = secrets.token_hex(32)
    _sessions[token] = request.username
    return {"token": token, "username": request.username}


@app.post("/api/login")
async def login(request: LoginRequest) -> dict[str, str]:
    with contextlib.closing(get_db_connection()) as connection:
        user = get_user_by_username(connection, request.username)

        if user is None:
            if request.username == "user" and request.password == "password":
                user_id = get_or_create_user_id(connection, "user")
                get_or_create_default_board(connection, user_id)
                token = secrets.token_hex(32)
                _sessions[token] = request.username
                return {"token": token, "username": request.username}
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if user["password_hash"] is None:
            if request.username == "user" and request.password == "password":
                user_id = user["id"]
                get_or_create_default_board(connection, user_id)
                token = secrets.token_hex(32)
                _sessions[token] = request.username
                return {"token": token, "username": request.username}
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not verify_password(request.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id = user["id"]
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM boards WHERE user_id = ?", (user_id,))
        if cursor.fetchone()["cnt"] == 0:
            cursor.execute(
                "INSERT INTO boards (user_id, name, board_json) VALUES (?, ?, ?)",
                (user_id, "My Board", json.dumps(DEFAULT_BOARD)),
            )
            connection.commit()

    token = secrets.token_hex(32)
    _sessions[token] = request.username
    return {"token": token, "username": request.username}


@app.post("/api/logout")
async def logout(
    username: str = Depends(get_current_user),
    authorization: str | None = Header(None),
) -> dict[str, str]:
    if authorization:
        token = authorization[7:]
        _sessions.pop(token, None)
    return {"status": "ok"}


# --- Multi-board endpoints ---

@app.get("/api/boards")
async def list_boards(username: str = Depends(get_current_user)) -> list[dict[str, Any]]:
    with contextlib.closing(get_db_connection()) as connection:
        user_id = get_or_create_user_id(connection, username)
        boards = get_boards_for_user(connection, user_id)
        if not boards:
            get_or_create_default_board(connection, user_id)
            boards = get_boards_for_user(connection, user_id)
        return boards


@app.post("/api/boards")
async def create_board(
    request: CreateBoardRequest, username: str = Depends(get_current_user)
) -> dict[str, Any]:
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Board name cannot be empty")
    with contextlib.closing(get_db_connection()) as connection:
        user_id = get_or_create_user_id(connection, username)
        board_id = create_board_for_user(connection, user_id, request.name.strip())
        return {"id": board_id, "name": request.name.strip()}


@app.get("/api/boards/{board_id}", response_model=BoardData)
async def get_board(board_id: int, username: str = Depends(get_current_user)) -> dict[str, Any]:
    with contextlib.closing(get_db_connection()) as connection:
        user_id = get_or_create_user_id(connection, username)
        board = get_board_by_id(connection, board_id, user_id)
        if board is None:
            raise HTTPException(status_code=404, detail="Board not found")
        return board


@app.put("/api/boards/{board_id}")
async def update_board_by_id(
    board_id: int, board: BoardData, username: str = Depends(get_current_user)
) -> dict[str, str]:
    with contextlib.closing(get_db_connection()) as connection:
        user_id = get_or_create_user_id(connection, username)
        if not save_board_by_id(connection, board_id, user_id, board.model_dump()):
            raise HTTPException(status_code=404, detail="Board not found")
        return {"status": "ok"}


@app.patch("/api/boards/{board_id}")
async def rename_board(
    board_id: int, request: RenameBoardRequest, username: str = Depends(get_current_user)
) -> dict[str, str]:
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Board name cannot be empty")
    with contextlib.closing(get_db_connection()) as connection:
        user_id = get_or_create_user_id(connection, username)
        if not rename_board_by_id(connection, board_id, user_id, request.name.strip()):
            raise HTTPException(status_code=404, detail="Board not found")
        return {"status": "ok"}


@app.delete("/api/boards/{board_id}")
async def delete_board(
    board_id: int, username: str = Depends(get_current_user)
) -> dict[str, str]:
    with contextlib.closing(get_db_connection()) as connection:
        user_id = get_or_create_user_id(connection, username)
        if not delete_board_by_id(connection, board_id, user_id):
            raise HTTPException(
                status_code=400, detail="Cannot delete the only board, or board not found"
            )
        return {"status": "ok"}


# --- Legacy single-board endpoints (kept for backward compatibility) ---

@app.get("/api/board", response_model=BoardData)
async def read_board(username: str = Depends(get_current_user)) -> dict[str, Any]:
    with contextlib.closing(get_db_connection()) as connection:
        user_id = get_or_create_user_id(connection, username)
        _, board = get_or_create_default_board(connection, user_id)
        return board


@app.put("/api/board")
async def update_board(
    board: BoardData, username: str = Depends(get_current_user)
) -> dict[str, str]:
    with contextlib.closing(get_db_connection()) as connection:
        user_id = get_or_create_user_id(connection, username)
        board_id, _ = get_or_create_default_board(connection, user_id)
        save_board_by_id(connection, board_id, user_id, board.model_dump())
        return {"status": "ok"}


# --- AI endpoint ---

def extract_json_object(content: str) -> str | None:
    start = content.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(content)):
        char = content[index]
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start : index + 1]
    return None


def parse_structured_ai_response(content: str) -> dict[str, Any] | None:
    json_text = extract_json_object(content)
    if not json_text:
        return None
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return None


@app.post("/api/ai")
async def proxy_ai(
    request: AIRequest,
    username: str = Depends(get_current_user),
) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not configured")

    system_message = (
        "You are an AI assistant for a Kanban board app. "
        "The user may ask you to update board state, add cards, or summarize the board. "
        "Always return a JSON object in your final answer with the keys `response` and optionally `updatedBoard`. "
        "If you include `updatedBoard`, it must match the board schema exactly. "
        "If no board changes are needed, omit `updatedBoard`."
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_message}]

    if request.board is not None:
        messages.append(
            {
                "role": "system",
                "content": (
                    "Here is the current board state in JSON. Use it as context for any updates:\n"
                    + json.dumps(request.board.model_dump(), indent=2)
                ),
            }
        )

    messages.append(
        {
            "role": "user",
            "content": (
                "Answer the user prompt below. "
                "Return only JSON with the keys `response` and optionally `updatedBoard`.\n\n"
                f"User prompt: {request.prompt}"
            ),
        }
    )

    payload = {"model": "openai/gpt-oss-120b:free", "messages": messages}
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers,
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenRouter request failed: {exc.__class__.__name__}",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to call OpenRouter")

    result_json = response.json()
    ai_message = (
        result_json.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
    )
    parsed = parse_structured_ai_response(ai_message)
    response_text = ai_message.strip()
    if parsed is not None and isinstance(parsed.get("response"), str):
        response_text = parsed["response"].strip()
    output: dict[str, Any] = {
        "status": "ok",
        "response": response_text,
        "raw": result_json,
    }

    if parsed is not None:
        output["structured"] = parsed
        board_payload = parsed.get("updatedBoard") or parsed.get("updated_board")
        if board_payload is not None:
            try:
                updated_board = BoardData.model_validate(board_payload)
                output["updatedBoard"] = updated_board.model_dump()
                with contextlib.closing(get_db_connection()) as connection:
                    user_id = get_or_create_user_id(connection, username)
                    if request.board_id is not None:
                        save_board_by_id(
                            connection, request.board_id, user_id, updated_board.model_dump()
                        )
                    else:
                        board_id, _ = get_or_create_default_board(connection, user_id)
                        save_board_by_id(connection, board_id, user_id, updated_board.model_dump())
            except Exception:
                output["boardValidationError"] = True

    return output


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
