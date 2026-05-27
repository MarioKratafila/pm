import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  onEdit: (cardId: string, title: string, details: string) => void;
  onDelete: (cardId: string) => void;
};

export const KanbanCard = ({ card, onEdit, onDelete }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(card.title);
  const [editDetails, setEditDetails] = useState(card.details);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const commitEdit = () => {
    const title = editTitle.trim() || card.title;
    const details = editDetails.trim() || card.details;
    onEdit(card.id, title, details);
    setEditing(false);
  };

  if (editing) {
    return (
      <article
        className="rounded-2xl border border-[var(--primary-blue)] bg-white px-3 py-3 shadow-[0_12px_24px_rgba(3,33,71,0.08)]"
        data-testid={`card-${card.id}`}
      >
        <input
          autoFocus
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitEdit();
            if (e.key === "Escape") setEditing(false);
          }}
          className="w-full bg-transparent font-display text-sm font-semibold text-[var(--navy-dark)] outline-none border-b border-[var(--stroke)] pb-1 mb-2"
          placeholder="Card title"
        />
        <textarea
          value={editDetails}
          onChange={(e) => setEditDetails(e.target.value)}
          rows={3}
          className="w-full resize-none bg-transparent text-xs leading-5 text-[var(--gray-text)] outline-none"
          placeholder="Details"
        />
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            onClick={commitEdit}
            className="rounded-full bg-[var(--secondary-purple)] px-3 py-1 text-xs font-semibold text-white"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="rounded-full border border-[var(--stroke)] px-3 py-1 text-xs font-semibold text-[var(--gray-text)]"
          >
            Cancel
          </button>
        </div>
      </article>
    );
  }

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "group relative rounded-2xl border border-transparent bg-white px-3 py-3 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="absolute right-2 top-2 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
        <button
          type="button"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={() => {
            setEditTitle(card.title);
            setEditDetails(card.details);
            setEditing(true);
          }}
          className="flex h-5 w-5 items-center justify-center rounded-full text-[var(--gray-text)] hover:bg-blue-50 hover:text-blue-400"
          aria-label={`Edit ${card.title}`}
        >
          <svg width="9" height="9" viewBox="0 0 9 9" fill="none" aria-hidden="true">
            <path d="M1 7.5l1.5-.5L7 2.5 6.5 2 2 6l-.5 1.5z" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <button
          type="button"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={() => onDelete(card.id)}
          className="flex h-5 w-5 items-center justify-center rounded-full text-[var(--gray-text)] hover:bg-red-50 hover:text-red-400"
          aria-label={`Delete ${card.title}`}
        >
          <svg width="9" height="9" viewBox="0 0 9 9" fill="none" aria-hidden="true">
            <path d="M1 1l7 7M8 1l-7 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
      </div>
      <div className="min-w-0 pr-4">
        <h4 className="font-display text-sm font-semibold text-[var(--navy-dark)]">
          {card.title}
        </h4>
        <p className="mt-1.5 break-words text-xs leading-5 text-[var(--gray-text)]">
          {card.details}
        </p>
      </div>
    </article>
  );
};
