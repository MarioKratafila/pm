# High level steps for project

Part 1: Plan

- Review the root project requirements, the frontend demo, and the existing workspace structure.
- Document the current frontend architecture and behavior.
- Define the backend layout, API routes, Docker build flow, and database persistence strategy.
- Confirm the plan and acceptance criteria with the user before writing code.

Success criteria:
- The plan lists explicit substeps, tests, and success criteria for every phase.
- The user approves the plan before moving to scaffolding.

Part 2: Scaffolding

- Create the backend directory and configure FastAPI.
- Create a Dockerfile for the full stack and a local build workflow.
- Add `scripts/start` and `scripts/stop` helpers for Mac, Windows, and Linux.
- Implement a minimal backend route that serves a simple HTML response and a basic API endpoint.

Success criteria:
- The backend container can start locally.
- `GET /` returns a served static page or static frontend placeholder.
- `GET /api/health` or equivalent returns a JSON response.
- Automated tests validate the backend startup route and API availability.

Part 3: Add in Frontend

- Build the existing Next.js frontend statically.
- Configure FastAPI to serve the built frontend at `/`.
- Ensure the Kanban board demo renders from the backend-served site.

Success criteria:
- `npm run build` succeeds and output is consumable.
- The app loads at `/` from the backend container and displays the Kanban board.
- Frontend unit tests and end-to-end smoke tests pass.

Part 4: Add in a fake user sign in experience

- Implement a login page or modal for initial access.
- Use hardcoded credentials: `user` / `password`.
- Add logout support.
- Protect the Kanban route until login succeeds.

Success criteria:
- Invalid credentials are rejected.
- Valid credentials show the Kanban board.
- Logout returns the user to the login screen.
- Tests cover login success, failure, and protected route behavior.

Part 5: Database modeling

- Design the database schema for users and boards.
- Persist board data as JSON in SQLite for simplicity.
- Document the chosen schema and any normalization decisions in `docs/`.
- Get user approval on the schema before implementation.

Success criteria:
- A documented schema exists in `docs/`.
- The schema supports one board per user and future multi-user extension.
- The user signs off on the schema before backend persistence work begins.

Part 6: Backend

- Add backend API routes for reading and updating a user board.
- Ensure the database is created if it does not exist.
- Implement persistence for columns, cards, and order via JSON stored in SQLite.
- Add backend tests for API behavior and database persistence.

Success criteria:
- `GET /api/board` returns the stored board for the signed-in user.
- `PUT /api/board` updates board state and persists changes.
- Database initialization works on first launch.
- Backend tests verify read/write persistence.

Part 7: Frontend + Backend

- Connect the frontend to the backend API for board data.
- Load the persisted board on app startup.
- Send updates for card moves, renames, additions, and deletions.
- Keep frontend state synchronized with backend data.

Success criteria:
- The board persists across browser refreshes.
- UI actions update backend state.
- Integration tests cover board load and update flows.

Part 8: AI connectivity

- Add a backend route to proxy prompts to OpenRouter.
- Use `OPENROUTER_API_KEY` from the root `.env` file.
- Confirm the AI service is reachable with a simple prompt.

Success criteria:
- Backend route returns a valid AI response.
- The `OPENROUTER_API_KEY` is loaded from environment.
- A test verifies the AI call path without requiring full chat UI.

Part 9: Structured AI output

- Send the current board JSON and user prompt to the AI.
- Define a structured response contract with optional board updates.
- Parse AI output in the backend and apply updates safely.
- Return the AI text response and any board updates to the frontend.

Success criteria:
- The AI route returns both a user-facing reply and structured update instructions.
- The backend applies valid board updates from the AI response.
- Tests verify response parsing and board update logic.

Part 10: AI chat sidebar

- Add a sidebar chat UI to the frontend.
- Allow the user to send questions and receive AI responses.
- If the AI returns board updates, refresh the Kanban UI automatically.
- Keep the chat experience simple and polished.

Success criteria:
- The chat sidebar works end to end.
- AI responses show in the UI.
- Board updates from the AI appear in the Kanban without manual refresh.
- E2E tests cover the chat flow and update refresh.

---

## Design decisions

- Frontend: Next.js app in `frontend/`, client-side board state with backend sync.
- Backend: FastAPI app in `backend/`, serving API routes at `/api/*`.
- Persistence: SQLite local database with `users` and `boards` tables.
- Board storage: JSON payload stored in `boards.board_json`, one board per user.
- User model: hardcoded user flow for MVP, database supports multiple users in future.
- API contract:
  - `GET /api/board?username=<user>` returns the board for that user.
  - `PUT /api/board?username=<user>` saves board updates.
  - `POST /api/ai` proxies prompts to OpenRouter.
- AI proxy: `https://api.openrouter.ai/v1/chat/completions` with `Authorization: Bearer <OPENROUTER_API_KEY>`.
- Env loading: `dotenv` loads `OPENROUTER_API_KEY` from the repo root `.env`.
- CORS: allow `http://localhost:3000`, methods `GET, PUT, POST, OPTIONS`, headers `*`.
- Frontend dev API base: `http://localhost:8000/api` for local development.
- Testing:
  - Backend tests use `unittest` and FastAPI `TestClient`.
  - Frontend tests use Vitest.
- Docker and container packaging remain part of the plan, but the current implementation is local dev-first.

> This plan is intentionally scoped as a linear MVP path. Each part should be completed and tested before moving to the next.
