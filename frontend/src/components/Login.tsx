"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";

type LoginProps = {
  onLogin: (username: string, token: string) => void;
};

export const Login = ({ onLogin }: LoginProps) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) {
        setError("Invalid credentials");
        return;
      }
      const data = (await response.json()) as { username: string; token: string };
      onLogin(data.username, data.token);
    } catch {
      setError("Unable to reach the server");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-2xl bg-white p-8 shadow-[var(--shadow)]"
      >
        <h2 className="text-2xl font-semibold mb-4">Sign in</h2>
        <label htmlFor="username" className="block text-sm font-medium text-[var(--gray-text)]">
          Username
        </label>
        <input
          id="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="mt-1 w-full rounded-xl border px-3 py-2"
          autoFocus
        />

        <label htmlFor="password" className="mt-4 block text-sm font-medium text-[var(--gray-text)]">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full rounded-xl border px-3 py-2"
        />

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <div className="mt-6 flex items-center justify-between">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white disabled:opacity-60"
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>
          <div className="text-sm text-[var(--gray-text)]">user / password</div>
        </div>
      </form>
    </div>
  );
};

export default Login;
