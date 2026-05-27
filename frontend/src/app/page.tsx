"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { Login } from "@/components/Login";
import { API_BASE } from "@/lib/api";

type Session = { user: string; token: string };

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("pm_session");
    if (stored) {
      setSession(JSON.parse(stored) as Session);
    }
  }, []);

  const handleLogin = (user: string, token: string) => {
    const s: Session = { user, token };
    localStorage.setItem("pm_session", JSON.stringify(s));
    setSession(s);
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
  };

  if (!session) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <KanbanBoard user={session.user} token={session.token} onLogout={handleLogout} />
  );
}
