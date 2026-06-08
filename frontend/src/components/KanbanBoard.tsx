"use client";

import { useEffect, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { ChatSidebar } from "@/components/ChatSidebar";
import { createId, initialData, moveCard, type BoardData } from "@/lib/kanban";
import { API_BASE, authHeaders } from "@/lib/api";

type KanbanBoardProps = {
  user: string;
  token: string;
  boardId: number;
  boardName: string;
  onLogout: () => void;
  onBackToBoards: () => void;
};

export const KanbanBoard = ({
  user,
  token,
  boardId,
  boardName,
  onLogout,
  onBackToBoards,
}: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData>(() => initialData);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [loadedBoardId, setLoadedBoardId] = useState<number | null>(null);
  const [saveError, setSaveError] = useState(false);
  const loading = loadedBoardId !== boardId;

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  useEffect(() => {
    let active = true;

    fetch(`${API_BASE}/boards/${boardId}`, { headers: authHeaders(token) })
      .then((response) => {
        if (response.status === 401) {
          onLogout();
          return null;
        }
        if (!response.ok) throw new Error("Failed to load board");
        return response.json() as Promise<BoardData>;
      })
      .then((data) => {
        if (!active) return;
        if (data) setBoard(data);
        setLoadedBoardId(boardId);
      })
      .catch((err) => {
        console.error(err);
        if (active) setLoadedBoardId(boardId);
      });

    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boardId]);

  const updateBoard = (nextBoard: BoardData) => {
    setBoard(nextBoard);
    fetch(`${API_BASE}/boards/${boardId}`, {
      method: "PUT",
      headers: authHeaders(token),
      body: JSON.stringify(nextBoard),
    })
      .then((response) => setSaveError(!response.ok))
      .catch(() => setSaveError(true));
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);
    if (!over || active.id === over.id) return;
    updateBoard({
      ...board,
      columns: moveCard(board.columns, active.id as string, over.id as string),
    });
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    updateBoard({
      ...board,
      columns: board.columns.map((col) =>
        col.id === columnId ? { ...col, title } : col
      ),
    });
  };

  const handleAddColumn = () => {
    updateBoard({
      ...board,
      columns: [
        ...board.columns,
        { id: createId("col"), title: "New Column", cardIds: [] },
      ],
    });
  };

  const handleDeleteColumn = (columnId: string) => {
    const column = board.columns.find((c) => c.id === columnId);
    if (!column) return;
    const removedCardIds = new Set(column.cardIds);
    updateBoard({
      ...board,
      columns: board.columns.filter((c) => c.id !== columnId),
      cards: Object.fromEntries(
        Object.entries(board.cards).filter(([id]) => !removedCardIds.has(id))
      ),
    });
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    updateBoard({
      ...board,
      cards: {
        ...board.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: board.columns.map((col) =>
        col.id === columnId ? { ...col, cardIds: [...col.cardIds, id] } : col
      ),
    });
  };

  const handleEditCard = (cardId: string, title: string, details: string) => {
    updateBoard({
      ...board,
      cards: {
        ...board.cards,
        [cardId]: { ...board.cards[cardId], title, details },
      },
    });
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    updateBoard({
      ...board,
      cards: Object.fromEntries(
        Object.entries(board.cards).filter(([id]) => id !== cardId)
      ),
      columns: board.columns.map((col) =>
        col.id === columnId
          ? { ...col, cardIds: col.cardIds.filter((id) => id !== cardId) }
          : col
      ),
    });
  };

  const activeCard = activeCardId ? board.cards[activeCardId] : null;

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-[var(--gray-text)]">Loading board...</p>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          {saveError && (
            <div className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">
              Board changes could not be saved. Check your connection and try again.
            </div>
          )}
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <button
                type="button"
                onClick={onBackToBoards}
                className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)] hover:text-[var(--primary-blue)] transition-colors"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path d="M8 2L4 6l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                All boards
              </button>
              <h1 className="font-display text-4xl font-semibold text-[var(--navy-dark)]">
                {boardName}
              </h1>
              <p className="mt-2 text-sm text-[var(--gray-text)]">
                Signed in as <span className="font-semibold text-[var(--navy-dark)]">{user}</span>
              </p>
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleAddColumn}
                className="rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-sm font-semibold shadow-[var(--shadow)] hover:bg-[var(--surface)] transition"
              >
                Add column
              </button>
              <button
                type="button"
                onClick={onLogout}
                className="rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-sm font-semibold shadow-[var(--shadow)]"
              >
                Logout
              </button>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_400px]">
          <div>
            <DndContext
              sensors={sensors}
              collisionDetection={closestCorners}
              onDragStart={handleDragStart}
              onDragEnd={handleDragEnd}
            >
              <section
                className="grid gap-4 overflow-x-auto pb-2"
                style={{
                  gridTemplateColumns: `repeat(${board.columns.length}, minmax(190px, 1fr))`,
                }}
              >
                {board.columns.map((column) => (
                  <KanbanColumn
                    key={column.id}
                    column={column}
                    cards={column.cardIds
                      .map((cardId) => board.cards[cardId])
                      .filter(Boolean)}
                    canDelete={board.columns.length > 1}
                    onRename={handleRenameColumn}
                    onDelete={handleDeleteColumn}
                    onAddCard={handleAddCard}
                    onEditCard={handleEditCard}
                    onDeleteCard={handleDeleteCard}
                  />
                ))}
              </section>
              <DragOverlay>
                {activeCard ? (
                  <div className="w-[200px]">
                    <KanbanCardPreview card={activeCard} />
                  </div>
                ) : null}
              </DragOverlay>
            </DndContext>
          </div>

          <ChatSidebar
            token={token}
            board={board}
            boardId={boardId}
            onUpdateBoard={updateBoard}
          />
        </div>
      </main>
    </div>
  );
};
