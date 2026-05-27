"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";

type LoginProps = {
  onLogin: (username: string, token: string) => void;
};

export const Login = ({ onLogin }: LoginProps) => {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (mode === "register") {
      if (password !== confirmPassword) {
        setError("Passwords do not match");
        return;
      }
      if (password.length < 6) {
        setError("Password must be at least 6 characters");
        return;
      }
    }

    setSubmitting(true);
    try {
      const endpoint = mode === "login" ? "/login" : "/register";
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: string };
        setError(body.detail ?? (mode === "login" ? "Invalid credentials" : "Registration failed"));
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

  const switchMode = () => {
    setMode(mode === "login" ? "register" : "login");
    setError(null);
    setConfirmPassword("");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-2xl bg-white p-8 shadow-[var(--shadow)]"
      >
        <h2 className="text-2xl font-semibold mb-1">
          {mode === "login" ? "Sign in" : "Create account"}
        </h2>
        <p className="text-sm text-[var(--gray-text)] mb-6">
          {mode === "login"
            ? "Welcome back to Kanban Studio."
            : "Choose a username and password."}
        </p>

        <label htmlFor="username" className="block text-sm font-medium text-[var(--gray-text)]">
          Username
        </label>
        <input
          id="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="mt-1 w-full rounded-xl border px-3 py-2"
          autoFocus
          autoComplete="username"
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
          autoComplete={mode === "login" ? "current-password" : "new-password"}
        />

        {mode === "register" && (
          <>
            <label
              htmlFor="confirm-password"
              className="mt-4 block text-sm font-medium text-[var(--gray-text)]"
            >
              Confirm password
            </label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="mt-1 w-full rounded-xl border px-3 py-2"
              autoComplete="new-password"
            />
          </>
        )}

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <div className="mt-6 flex items-center justify-between">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white disabled:opacity-60"
          >
            {submitting
              ? mode === "login"
                ? "Signing in..."
                : "Creating..."
              : mode === "login"
                ? "Sign in"
                : "Create account"}
          </button>
          <button
            type="button"
            onClick={switchMode}
            className="text-sm text-[var(--primary-blue)] hover:underline"
          >
            {mode === "login" ? "Create account" : "Sign in instead"}
          </button>
        </div>

        {mode === "login" && (
          <p className="mt-4 text-xs text-[var(--gray-text)]">
            Default credentials: user / password
          </p>
        )}
      </form>
    </div>
  );
};

export default Login;
