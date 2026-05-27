"use client";

import { useEffect, useState } from "react";
import { API_BASE, authHeaders } from "@/lib/api";

type BoardMeta = {
  id: number;
  name: string;
  updated_at: string;
  card_count: number;
};

type BoardDashboardProps = {
  user: string;
  token: string;
  onSelectBoard: (boardId: number, boardName: string) => void;
  onLogout: () => void;
};

export const BoardDashboard = ({ user, token, onSelectBoard, onLogout }: BoardDashboardProps) => {
  const [boards, setBoards] = useState<BoardMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newBoardName, setNewBoardName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const fetchBoards = async () => {
    const response = await fetch(`${API_BASE}/boards`, { headers: authHeaders(token) });
    if (!response.ok) throw new Error("Failed to load boards");
    return (await response.json()) as BoardMeta[];
  };

  useEffect(() => {
    fetch(`${API_BASE}/boards`, { headers: authHeaders(token) })
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load boards");
        return r.json() as Promise<BoardMeta[]>;
      })
      .then(setBoards)
      .catch(() => setError("Failed to load boards"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = newBoardName.trim();
    if (!name) return;
    setCreating(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/boards`, {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify({ name }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: string };
        setError(body.detail ?? "Failed to create board");
        return;
      }
      setNewBoardName("");
      const updated = await fetchBoards();
      setBoards(updated);
    } catch {
      setError("Failed to create board");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (boardId: number) => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/boards/${boardId}`, {
        method: "DELETE",
        headers: authHeaders(token),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: string };
        setError(body.detail ?? "Failed to delete board");
        return;
      }
      setBoards((prev) => prev.filter((b) => b.id !== boardId));
    } catch {
      setError("Failed to delete board");
    }
  };

  const startRename = (board: BoardMeta) => {
    setRenamingId(board.id);
    setRenameValue(board.name);
  };

  const commitRename = async (boardId: number) => {
    const name = renameValue.trim();
    if (!name) {
      setRenamingId(null);
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/boards/${boardId}`, {
        method: "PATCH",
        headers: authHeaders(token),
        body: JSON.stringify({ name }),
      });
      if (response.ok) {
        setBoards((prev) => prev.map((b) => (b.id === boardId ? { ...b, name } : b)));
      }
    } catch {
      // ignore rename errors silently
    } finally {
      setRenamingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-[var(--gray-text)]">Loading boards...</p>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[900px] flex-col gap-8 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-4 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Project Management
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-2 text-sm text-[var(--gray-text)]">
                Signed in as <span className="font-semibold text-[var(--navy-dark)]">{user}</span>
              </p>
            </div>
            <button
              type="button"
              onClick={onLogout}
              className="rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-sm font-semibold shadow-[var(--shadow)]"
            >
              Logout
            </button>
          </div>
        </header>

        {error && (
          <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        <section className="rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <h2 className="font-display text-xl font-semibold text-[var(--navy-dark)] mb-6">
            Your Boards
          </h2>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {boards.map((board) => (
              <div
                key={board.id}
                className="group relative flex flex-col gap-3 rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] p-5 shadow-[var(--shadow)] transition hover:shadow-md"
              >
                {renamingId === board.id ? (
                  <input
                    autoFocus
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onBlur={() => commitRename(board.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") commitRename(board.id);
                      if (e.key === "Escape") setRenamingId(null);
                    }}
                    className="font-display text-base font-semibold text-[var(--navy-dark)] bg-transparent outline-none border-b border-[var(--primary-blue)] w-full"
                  />
                ) : (
                  <h3
                    className="font-display text-base font-semibold text-[var(--navy-dark)] cursor-pointer hover:text-[var(--primary-blue)] transition-colors"
                    onClick={() => startRename(board)}
                    title="Click to rename"
                  >
                    {board.name}
                  </h3>
                )}

                <p className="text-xs text-[var(--gray-text)]">
                  {board.card_count} {board.card_count === 1 ? "card" : "cards"}
                </p>

                <div className="mt-auto flex gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => onSelectBoard(board.id, board.name)}
                    className="flex-1 rounded-full bg-[var(--secondary-purple)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
                  >
                    Open
                  </button>
                  {boards.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleDelete(board.id)}
                      className="rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold text-[var(--gray-text)] transition hover:bg-red-50 hover:text-red-500 hover:border-red-200"
                      aria-label={`Delete ${board.name}`}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            ))}

            <form
              onSubmit={handleCreate}
              className="flex flex-col gap-3 rounded-2xl border border-dashed border-[var(--stroke)] p-5"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                New Board
              </p>
              <input
                value={newBoardName}
                onChange={(e) => setNewBoardName(e.target.value)}
                placeholder="Board name"
                className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              />
              <button
                type="submit"
                disabled={creating || !newBoardName.trim()}
                className="rounded-full bg-[var(--accent-yellow)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--navy-dark)] transition hover:brightness-110 disabled:opacity-50"
              >
                {creating ? "Creating..." : "Create board"}
              </button>
            </form>
          </div>
        </section>
      </main>
    </div>
  );
};
