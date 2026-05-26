# Database schema for the MVP

## Purpose

This document defines the database model for the project management MVP. The goal is to support one persistent Kanban board per user, while keeping the implementation simple and extensible for future multi-user support.

## Design goals

- Keep the schema minimal.
- Persist the full board state as JSON so the frontend model can be stored and restored easily.
- Support one board per user today and allow future multi-user extension.
- Use SQLite locally with automatic database creation.

## Tables

### `users`

Fields:
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `username TEXT UNIQUE NOT NULL`
- `created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP`

Notes:
- The backend login is still MVP-level; the user table is included to support future authentication and per-user boards.
- For now, the frontend uses hardcoded credentials, but the backend will map those credentials to a user record by username.

### `boards`

Fields:
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE`
- `board_json TEXT NOT NULL`
- `updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP`

Notes:
- Each user has exactly one board row (`user_id` is unique).
- `board_json` stores the full serialized board state.
- `updated_at` allows basic auditing and invalidation logic.

## Why JSON storage?

The frontend already models the board as a JSON-compatible shape in `frontend/src/lib/kanban.ts`:

```ts
export type Card = {
  id: string;
  title: string;
  details: string;
};

export type Column = {
  id: string;
  title: string;
  cardIds: string[];
};

export type BoardData = {
  columns: Column[];
  cards: Record<string, Card>;
};
```

This schema is a strong fit for JSON storage because it preserves:

- column ordering and titles
- card details keyed by ID
- card order within each column

Storing the board as JSON avoids early normalization and keeps backend persistence simple.

## Example `board_json`

```json
{
  "columns": [
    { "id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"] },
    { "id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"] },
    { "id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"] },
    { "id": "col-review", "title": "Review", "cardIds": ["card-6"] },
    { "id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"] }
  ],
  "cards": {
    "card-1": { "id": "card-1", "title": "Align roadmap themes", "details": "Draft quarterly themes with impact statements and metrics." },
    "card-2": { "id": "card-2", "title": "Gather customer signals", "details": "Review support tags, sales notes, and churn feedback." }
  }
}
```

## Persistence strategy

- On startup, the backend will open a local SQLite database file in `backend/`.
- If the file does not exist, the backend will create it and initialize the `users` and `boards` tables.
- When a user requests their board, the backend will look up the `users` row and return the associated `board_json`.
- When the board changes, the backend will update the `board_json` and `updated_at` fields.

## Future extension

This model supports future improvements without schema changes:

- additional users and authentication
- multiple boards per user by splitting `boards` into `boards` and `board_states`
- audit/history tables for board changes
- server-side user sessions and permissions

## Approval

If this schema looks good, the next step is to implement it in the backend and add API routes for board read/write.
