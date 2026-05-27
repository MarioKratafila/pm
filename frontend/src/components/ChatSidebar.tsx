"use client";

import { useState } from "react";
import type { BoardData } from "@/lib/kanban";
import { API_BASE, authHeaders } from "@/lib/api";

type ChatSidebarProps = {
  token: string;
  board: BoardData;
  onUpdateBoard: (board: BoardData) => void;
};

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  id: string;
};

export const ChatSidebar = ({ token, board, onUpdateBoard }: ChatSidebarProps) => {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addMessage = (message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  };

  const handleSend = async () => {
    const trimmed = prompt.trim();
    if (!trimmed) {
      return;
    }

    setError(null);
    setStatus(null);
    setSending(true);

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: trimmed,
    };
    addMessage(userMessage);
    setPrompt("");

    try {
      const response = await fetch(`${API_BASE}/ai`, {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify({ prompt: trimmed, board }),
      });

      if (!response.ok) {
        let detail = "AI request failed";
        try {
          const errorBody = (await response.json()) as { detail?: string };
          if (typeof errorBody.detail === "string" && errorBody.detail.trim()) {
            detail = errorBody.detail;
          }
        } catch {
          // Keep default message when response is not valid JSON.
        }
        throw new Error(detail);
      }

      const data = await response.json();
      const assistantText =
        typeof data.response === "string"
          ? data.response
          : JSON.stringify(data.raw ?? data, null, 2);

      addMessage({
        id: crypto.randomUUID(),
        role: "assistant",
        text: assistantText,
      });

      if (data.boardValidationError) {
        setStatus("AI attempted a board update but the response format was invalid.");
      } else if (data.updatedBoard) {
        onUpdateBoard(data.updatedBoard as BoardData);
        setStatus("AI suggested updates applied to the board.");
      } else {
        setStatus("AI response received. No board changes were detected.");
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to reach the AI service."
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <aside className="rounded-[32px] border border-[var(--stroke)] bg-white/90 p-6 shadow-[var(--shadow)] backdrop-blur">
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
          AI Assistant
        </p>
        <h2 className="mt-3 text-2xl font-semibold text-[var(--navy-dark)]">
          Help the board
        </h2>
        <p className="mt-3 text-sm leading-6 text-[var(--gray-text)]">
          Ask the AI to update the board, add cards, or summarize progress.
        </p>
      </div>

      <div className="space-y-3">
        <label htmlFor="ai-prompt" className="block text-sm font-medium text-[var(--gray-text)]">
          Your prompt
        </label>
        <textarea
          id="ai-prompt"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={4}
          className="w-full resize-none rounded-3xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
          placeholder="Example: Move the highest-priority card to In Progress and rename the backlog column to Ready."
        />
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <button
            type="button"
            onClick={handleSend}
            disabled={sending}
            className="inline-flex w-full items-center justify-center rounded-full bg-[var(--secondary-purple)] px-5 py-3 text-sm font-semibold uppercase tracking-wide text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
          >
            {sending ? "Sending…" : "Send to AI"}
          </button>
          <div className="text-xs text-[var(--gray-text)]">
            Responses may include board updates.
          </div>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        {status && (
          <div className="rounded-2xl bg-[var(--surface)] px-4 py-3 text-sm text-[var(--navy-dark)]">
            {status}
          </div>
        )}
        {error && (
          <div className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}
      </div>

      <div className="mt-6 text-xs uppercase tracking-[0.28em] text-[var(--gray-text)]">
        Conversation
      </div>
      <div className="mt-3 max-h-[420px] space-y-4 overflow-y-auto pr-1">
        {messages.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-[var(--stroke)] bg-[var(--surface)] p-4 text-sm text-[var(--gray-text)]">
            Send a prompt to start the chat.
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={
                message.role === "user"
                  ? "rounded-3xl bg-[var(--primary-blue)]/10 p-4 text-sm text-[var(--navy-dark)]"
                  : "rounded-3xl bg-[var(--surface)] p-4 text-sm text-[var(--navy-dark)]"
              }
            >
              <div className="mb-2 text-[var(--gray-text)] uppercase tracking-[0.2em] text-[0.65rem]">
                {message.role === "user" ? "You" : "AI"}
              </div>
              <div className="whitespace-pre-wrap break-words">{message.text}</div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
};
