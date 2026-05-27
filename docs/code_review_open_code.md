# Code Review: Project Management MVP

**Date:** 2026-05-27
**Reviewer:** opencode (big-pickle)
**Scope:** Full project (backend, frontend, scripts, Docker, docs, config)

---

## Architecture Overview

Two-tier architecture:
- **Frontend:** Next.js 16 (App Router, Tailwind CSS v4, `@dnd-kit`) built to static export
- **Backend:** Single-file Python FastAPI app serving both the REST API and the static frontend
- **Database:** SQLite with two tables (`users`, `boards`), board state stored as a JSON blob
- **Deployment:** Single Docker container running Uvicorn (no nginx, no separate Node server)

The architecture is appropriate for an MVP: simple, minimal moving parts, single container. The design decision to serve the built Next.js output directly from FastAPI (rather than running a separate Node server or nginx) reduces operational complexity.

---

## Critical Issues

### C1: API key baked into Docker image

**Files:** `Dockerfile:7`, `.dockerignore:8`
**Severity:** Critical

The Dockerfile runs `COPY .env /app/.env` (line 7), which embeds the `.env` file (containing `OPENROUTER_API_KEY`) into every built image. The `.dockerignore` has `.env` commented out on line 8 (`#.env`), so the file is not excluded from the build context. Anyone with access to the image can extract the key.

The `.env` should be passed to the container at runtime (e.g., `--env-file` or docker compose `env_file`), not baked into the image. The `.dockerignore` entry should be uncommented to prevent accidental inclusion during a `COPY .` or similar instruction.

---

## High Priority Issues

### H1: No real authentication

**Files:** `backend/main.py:78-100` (login/logout), `backend/main.py:216-235` (`get_current_user`)
**Severity:** High

Authentication uses an in-memory `_sessions: dict[str, str]` mapping tokens to usernames. Issues:
- All sessions are lost on server restart, forcing all users to re-login
- Tokens are simple hex strings (no JWT, no signature) — any token can be forged if the value space is guessed
- Once authenticated, the server trusts the client entirely; there is no server-side verification that a token belongs to the user whose data is being accessed
- Tokens never expire; no TTL, no refresh mechanism
- Logout only removes the token but there is no way to revoke all sessions for a user

For an MVP this is acceptable in simplicity, but it should be documented as a known limitation and flagged for early improvement.

### H2: No server-side board validation on save

**File:** `backend/main.py:262-280` (`write_board`)
**Severity:** High

The `PUT /api/board` endpoint deserializes the request body into a `BoardData` Pydantic model, which validates structural types (strings, lists, dicts) but performs no referential integrity checks:
- Card IDs referenced in `column.cardIds` may not exist in the `cards` dict
- Cards in the `cards` dict may not be referenced by any column
- Duplicate card IDs across columns are not detected
- No size limits on the board JSON

A corrupted request (from a buggy client, AI hallucination, or network corruption) could silently persist an inconsistent board state.

### H3: Loading state fallback overwrites real data

**Files:** `frontend/src/components/KanbanBoard.tsx` (around line 60-80)
**Severity:** High

When the initial `GET /api/board` request fails (e.g., network error, server down), the loading state transitions to false but the `board` state remains set to the hardcoded `initialData`. The user sees demo cards that don't correspond to their persisted board. If the user then makes any mutation (drag, add card, etc.), the PUT request overwrites their real persisted data with the demo data.

The board should remain in an error state when the API fails, or at minimum prevent saves until a successful reload.

---

## Medium Priority Issues

### M1: Stale documentation

**Files:** `docs/code_review.md`, `backend/AGENTS.md`
**Severity:** Medium

The existing `docs/code_review.md` lists 13 issues, most of which have already been fixed:
- Silent save failures (fixed with `saveError` state + banner)
- Duplicated `API_BASE` (fixed — centralized in `src/lib/api.ts`)
- Deprecated `@app.on_event("startup")` (fixed — uses `lifespan`)
- ChatSidebar label linking (fixed — `htmlFor`/`id` match)
- `boardValidationError` not checked (fixed)
- Weak message IDs (fixed — uses `crypto.randomUUID()`)

This document needs updating or archiving to avoid confusion. Additionally, `backend/AGENTS.md` describes a different API structure (mounting static at `/static`, only health/hello endpoints) than what is actually implemented (mounting at `/_next`, 7 API endpoints).

### M2: Dual dependency management

**Files:** `backend/requirements.txt`, `backend/pyproject.toml`
**Severity:** Medium

Both files list the same four dependencies (`fastapi`, `uvicorn`, `httpx`, `python-multipart`). `pydantic` is not listed in either (it's a transitive dependency of FastAPI). If FastAPI ever changes its dependency graph, the code could break. Consolidate to a single source of truth (`pyproject.toml`) and generate `requirements.txt` from it, or add `pydantic` explicitly.

### M3: Test fragility

**File:** `backend/test_main.py:83-97`
**Severity:** Medium

The backend tests define `FakeResponse` and `FakeClient` classes that don't properly implement the async context manager protocol. They work because the test mocks `main.httpx.AsyncClient`, but this tightly couples the tests to the implementation detail of how HTTPX is imported. A refactor that changes the import style or uses a different HTTP client would silently break the tests.

**File:** `frontend/src/components/KanbanBoard.test.tsx`
**Severity:** Medium

The component test stubs `globalThis.fetch` with `vi.stubGlobal()`. While cleanup is handled, the mock returns `initialData` for all GET requests, meaning the test never validates actual API response handling or error states. The mock doesn't exercise the real fetch flow.

### M4: Session token never expires

**File:** `backend/main.py:78-100`
**Severity:** Medium

Tokens in `_sessions` live forever (until server restart). There is no TTL, no sliding expiration, and no mechanism to expire tokens on the server side. Combined with no token rotation, a leaked token gives permanent access.

### M5: Card model has no content validation

**File:** `backend/main.py:180-190` (Pydantic models)
**Severity:** Medium

The `Card.details` field is a plain `str` with no constraints. Empty strings, excessively long strings (e.g., 1MB of text), and malformed data from the AI are accepted without validation. Add `min_length`, `max_length`, or a custom validator.

---

## Low Priority Issues

### L1: Docker runs as root

**File:** `Dockerfile`
**Severity:** Low

No `USER` directive is set. The Uvicorn process runs as root inside the container. While acceptable for a local MVP, this is a security anti-pattern. Add `RUN adduser --disabled-password appuser && USER appuser`.

### L2: No HEALTHCHECK in Dockerfile

**File:** `Dockerfile`
**Severity:** Low

The container has no `HEALTHCHECK` instruction. Orchestrators (or docker compose) cannot determine if the application is actually ready. Add `HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8000/api/health || exit 1`.

### L3: Fragile static file path in Dockerfile

**File:** `Dockerfile:12-14`
**Severity:** Low

The Dockerfile copies `frontend/.next/server/app/index.html` to the backend static directory. This path depends on Next.js 16's static export behavior for the App Router. If the root `page.tsx` is ever made dynamic (it's currently `"use client"` but still statically exportable), this path will change and the Docker build will silently fail (or produce a broken container with a missing SPA).

Consider using `npx next export` (or the static export output) more generically, or validate the expected file exists during build.

### L4: Catch-all route serves any file

**File:** `backend/main.py:407-420`
**Severity:** Low

The `@app.get("/{full_path:path}")` route serves any matching file in `STATIC_DIR`. Currently mitigated by the `target_file.is_file()` check, but if the app is ever extended with user-uploaded content in the same directory tree, this could become a path traversal or information disclosure vector.

### L5: No request size limits

**File:** `backend/main.py` (all endpoints)
**Severity:** Low

None of the endpoints enforce request body size limits. A large board payload or a maliciously crafted request could cause memory issues. FastAPI supports `max_length` on Body parameters and middleware-level size limits via `uvicorn --limit-max-request-body`.

### L6: Test for login failure is incomplete

**File:** `backend/test_main.py`
**Severity:** Low

The test `test_login_failure` only checks that a bad password returns status 401. It does not verify the response body contains an error message, nor does it test that subsequent requests with a bad token are rejected.

---

## Previously Fixed Issues

The following issues from the existing `docs/code_review.md` have been resolved:

| Issue | Resolution |
|---|---|
| `start.sh` missing build steps | Build steps added |
| Silent save failures | `saveError` state + red banner |
| Duplicated `API_BASE` | Centralized in `src/lib/api.ts` |
| Deprecated `@app.on_event("startup")` | Uses `lifespan` async context manager |
| Unlinked label in ChatSidebar | `htmlFor`/`id` match |
| `boardValidationError` not checked | Displayed in ChatSidebar |
| Weak message IDs with `Date.now()` | Uses `crypto.randomUUID()` |

---

## Positive Observations

- Clean separation of concerns between frontend and backend
- Well-structured drag-and-drop logic using `@dnd-kit` with proper collision detection
- Good use of Pydantic models for API request/response validation
- E2E tests with Playwright cover the critical user flows (login, board load, add card, drag card)
- Vitest setup is clean and modern
- The `KanbanBoard` component handles loading, error, and empty states (though error handling has the H3 issue)
- Python test coverage includes health, auth, board CRUD, and AI proxy
- Start/stop scripts for all three platforms (Mac, PC, Linux) — good DX consideration
- SPA routing fallback is correctly implemented for client-side navigation
- The AI chat integration is well-structured with structured JSON response parsing

---

## Recommendations (Priority Order)

1. **Immediate:** Uncomment `.env` in `.dockerignore` and change the Dockerfile to not bake secrets into the image (use `--env-file` at runtime instead).

2. **Before MVP launch:** Fix H3 (loading state overwrite) — prevent saves until a successful board load. Add server-side board validation (H2). Add session token expiry (H4).

3. **Near-term:** Consolidate dependency management to `pyproject.toml` only (M2). Update stale documentation (M1). Add Docker HEALTHCHECK and USER directive (L1, L2).

4. **Tech debt:** Refactor backend tests to not rely on implementation-specific mocking (M3). Add `Card.details` validation (M5). Add request size limits (L5). Harden the static catch-all route (L4).
