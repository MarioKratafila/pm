"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { Login } from "@/components/Login";

export default function Home() {
  const [user, setUser] = useState<string | null>(null);

  useEffect(() => {
    setUser(localStorage.getItem("pm_user"));
  }, []);

  const handleLogin = (username: string) => {
    localStorage.setItem("pm_user", username);
    setUser(username);
  };

  const handleLogout = () => {
    localStorage.removeItem("pm_user");
    setUser(null);
  };

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return <KanbanBoard user={user} onLogout={handleLogout} />;
}
