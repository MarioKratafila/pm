"use client";

import { useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { BoardDashboard } from "@/components/BoardDashboard";
import { Login } from "@/components/Login";
import { API_BASE } from "@/lib/api";

type Session = { user: string; token: string };
type SelectedBoard = { id: number; name: string };

function loadSession(): Session | null {
  if (typeof window === "undefined") return null;
  const stored = localStorage.getItem("pm_session");
  return stored ? (JSON.parse(stored) as Session) : null;
}

export default function Home() {
  const [session, setSession] = useState<Session | null>(loadSession);
  const [selectedBoard, setSelectedBoard] = useState<SelectedBoard | null>(null);

  const handleLogin = (user: string, token: string) => {
    const next: Session = { user, token };
    localStorage.setItem("pm_session", JSON.stringify(next));
    setSession(next);
    setSelectedBoard(null);
  };

  const handleLogout = () => {
    if (session) {
      void fetch(`${API_BASE}/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session.token}` },
      });
    }
    localStorage.removeItem("pm_session");
    setSession(null);
    setSelectedBoard(null);
  };

  if (!session) {
    return <Login onLogin={handleLogin} />;
  }

  if (!selectedBoard) {
    return (
      <BoardDashboard
        user={session.user}
        token={session.token}
        onSelectBoard={(id, name) => setSelectedBoard({ id, name })}
        onLogout={handleLogout}
      />
    );
  }

  return (
    <KanbanBoard
      user={session.user}
      token={session.token}
      boardId={selectedBoard.id}
      boardName={selectedBoard.name}
      onLogout={handleLogout}
      onBackToBoards={() => setSelectedBoard(null)}
    />
  );
}
