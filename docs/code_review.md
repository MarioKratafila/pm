# Code review

Reviewed 2026-05-27. All 10 MVP parts are complete and all tests pass. The findings below are ordered by priority.

---

## High priority

### 1. `start.sh` will fail on a clean clone

`scripts/start.sh` skips the frontend build step. The Dockerfile contains:

```dockerfile
COPY frontend/.next/server/app/index.html /app/backend/static/index.html
COPY frontend/.next/static /app/backend/static/_next/static
```

If the frontend has never been built, these paths don't exist and `docker build` fails. `scripts/start.ps1` correctly runs `npm install && npm run build` first; `start.sh` does not.

**Fix:** Add the build steps to `start.sh`:

```bash
echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..
```

---

### 2. No authentication on the board API

The username is passed as a plain query parameter (`?username=user`) with no session, token, or signature. Any client on the same network can read or overwrite any user's board by supplying a different username. The `/api/ai` endpoint has the same gap.

This is noted as an MVP limitation, but it's worth being explicit: the hardcoded-credential login is purely client-side (localStorage). The backend applies no trust boundary between users.

**Fix for a next iteration:** Issue a signed session token on login (e.g. a signed cookie or a JWT) and validate it on every board/AI request instead of accepting the username as input.

---

### 3. Board save failures are invisible to the user

`saveBoard` in `KanbanBoard.tsx:42` catches exceptions and only logs to the console:

```ts
} catch (error) {
  console.error("Could not save board", error);
}
```

If the backend is unreachable, the user's drag, rename, or card edit appears to succeed in the UI but is silently lost. The same path is triggered when the AI returns a board update.

**Fix:** Surface a non-blocking error state (e.g. a transient banner) when the save fails so the user knows their change wasn't persisted.

---

## Medium priority

### 4. `API_BASE` is duplicated

Both `KanbanBoard.tsx:24` and `ChatSidebar.tsx:18` independently define:

```ts
const API_BASE =
  process.env.NODE_ENV === "development"
    ? "http://localhost:8000/api"
    : "/api";
```

**Fix:** Move this to `src/lib/api.ts` (or similar) and import it in both components.

---

### 5. `loading` state is tracked but never rendered

`KanbanBoard.tsx` sets `loading = true` on mount and `false` after the board fetch resolves, but the render path never checks this flag. While the board loads, the user sees `initialData` (the hardcoded placeholder cards), then sees it replaced by the real board. On a slow connection this is a visible flash of wrong content.

**Fix:** Render a loading skeleton or suppress the board render until `loading` is false.

---

### 6. `@app.on_event("startup")` is deprecated

`backend/main.py:136` uses:

```python
@app.on_event("startup")
async def startup() -> None:
    init_db()
```

This decorator was deprecated in FastAPI 0.93 in favour of the `lifespan` context manager. It still works but will generate deprecation warnings in future versions.

**Fix:**

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Project Management Backend", lifespan=lifespan)
```

---

### 7. ChatSidebar textarea has an unlinked label

`ChatSidebar.tsx:119` has a `<label>` with text "Your prompt" but no `htmlFor` attribute, and the `<textarea>` has no matching `id`. This is the same accessibility issue that was fixed in `Login.tsx` during the test run.

**Fix:**

```tsx
<label htmlFor="ai-prompt" ...>Your prompt</label>
<textarea id="ai-prompt" ...>
```

---

### 8. `boardValidationError` response field is never checked by the frontend

When the AI returns a board update that fails Pydantic validation, the backend sets `boardValidationError: true` in the response (`main.py:350`). `ChatSidebar.tsx` checks `data.updatedBoard` but never checks `data.boardValidationError`, so the user gets no indication that the AI attempted a board change that was rejected.

**Fix:** Check for `data.boardValidationError` in `ChatSidebar.handleSend` and add it to the status message.

---

## Low priority

### 9. Two dependency files for the backend

`backend/pyproject.toml` and `backend/requirements.txt` list identical dependencies. The Dockerfile uses `requirements.txt` while the `pyproject.toml` exists for tooling. Having two files means updates must be applied twice.

**Fix:** The Dockerfile could use `pip install -e .` from `pyproject.toml` only, or `uv pip sync requirements.txt` if keeping both. At minimum, add a note that they must be kept in sync.

---

### 10. `pydantic` is not listed in either dependency file

`main.py` imports `pydantic.BaseModel` directly. Pydantic is a direct FastAPI dependency so it will always be present, but it's good practice to list direct dependencies explicitly.

**Fix:** Add `pydantic>=2.0.0` to both `requirements.txt` and `pyproject.toml`.

---

### 11. Message IDs use `Date.now()`

`ChatSidebar.tsx:45` and `:83` generate message IDs with `` `user-${Date.now()}` `` and `` `assistant-${Date.now()}` ``. Two messages arriving within the same millisecond would share a key and cause a React warning.

**Fix:** Use `crypto.randomUUID()` which is available in all modern browsers.

---

### 12. Docker image runs as root

The Dockerfile has no `USER` directive, so the container process runs as root. For a local-only MVP this is low risk, but it's a bad habit.

**Fix:** Add before `CMD`:

```dockerfile
RUN adduser --disabled-password --gecos "" appuser
USER appuser
```

---

### 13. No `HEALTHCHECK` in Dockerfile

Docker has no way to report container health, which means `docker ps` will show the container as healthy even if the Python process has crashed.

**Fix:**

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/api/health || exit 1
```

---

## Test coverage gaps

| Gap | Suggested addition |
|-----|--------------------|
| Login component: invalid credentials shows error | Unit test in `Login.test.tsx` |
| Login component: valid credentials calls `onLogin` | Unit test in `Login.test.tsx` |
| Logout returns to login screen | E2E test in `kanban.spec.ts` |
| Login with wrong credentials shows error message | E2E test in `kanban.spec.ts` |
| ChatSidebar: renders, sends a prompt, displays response | Unit test with mocked fetch |
| Backend: `GET /api/board` without username returns 422 | `test_main.py` |
| Backend: `PUT /api/board` with invalid schema returns 422 | `test_main.py` |
| Backend: `GET /api/health` and `GET /api/hello` | `test_main.py` |

---

## Summary

| Priority | Count | Key items |
|----------|-------|-----------|
| High | 3 | `start.sh` missing build step; no API auth; silent save failures |
| Medium | 5 | Duplicate `API_BASE`; unused `loading` state; deprecated startup event; unlinked label; unhandled `boardValidationError` |
| Low | 5 | Dual dependency files; missing pydantic declaration; weak message IDs; container runs as root; no healthcheck |
| Tests | 8 | Login unit tests; logout E2E; error paths in backend tests |
