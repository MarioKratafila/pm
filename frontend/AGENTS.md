# Frontend Agent Guide

## Purpose
This file explains the current frontend implementation and the work needed to move the MVP from a standalone demo to a backend-integrated Kanban app.

## Current frontend state
- Directory: `frontend/`
- Framework: Next.js app router (`next` 16.1.6)
- Styling: Tailwind CSS with PostCSS
- Drag-and-drop: `@dnd-kit/core` and `@dnd-kit/sortable`
- UI: single-board Kanban with five columns
- State: stored locally in React state inside `KanbanBoard`
- Auth: not implemented
- Backend: not implemented
- Database: not implemented
- AI: not implemented

## Entry point
- `frontend/src/app/page.tsx` renders `<KanbanBoard />`

## Core data model
- `frontend/src/lib/kanban.ts`
  - `Card` type: `{ id, title, details }`
  - `Column` type: `{ id, title, cardIds }`
  - `BoardData` type: `{ columns, cards }`
  - `initialData` sets up five columns and eight cards
  - `moveCard()` handles card reordering and cross-column moves
  - `createId()` generates new card IDs

## Main components
- `KanbanBoard.tsx`
  - holds board state and drag overlay state
  - handles column rename, add card, delete card, and drag end
  - renders `KanbanColumn` for each column
- `KanbanColumn.tsx`
  - droppable column wrapper
  - renders cards with `SortableContext`
  - includes `NewCardForm`
- `KanbanCard.tsx`
  - sortable card item with remove button
- `KanbanCardPreview.tsx`
  - drag overlay preview for the active card
- `NewCardForm.tsx`
  - expandable form to create a new card

## Current behavior
- Rename column titles inline
- Add a new card to any column
- Delete a card from any column
- Drag cards within a column and across columns
- Local state updates immediately in the browser

## Tests and tooling
- Unit test runner: `vitest`
- UI test tooling: `@testing-library/react`, `@testing-library/user-event`
- E2E: `@playwright/test`
- Run commands:
  - `npm run dev`
  - `npm run build`
  - `npm run test:unit`
  - `npm run test:e2e`

## Next work items
- Create backend APIs and integrate with frontend state
- Add fake login/logout flow
- Persist board data in SQLite
- Add AI sidebar and structured AI board updates
- Ensure the frontend build is served by FastAPI in Docker

## Notes
- Keep this file updated whenever the frontend data model or core architecture changes.
