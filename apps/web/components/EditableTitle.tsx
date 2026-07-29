"use client";

import { ElementType, useEffect, useRef, useState } from "react";

import Spinner from "@/components/common/Spinner";

/**
 * A title that renames inline. The pencil affordance appears only on hover;
 * clicking it swaps in an input. Enter/blur commits, Escape cancels. Sizing is
 * inherited from `className` so the input matches the heading it replaces.
 */
export default function EditableTitle({
  value,
  onSave,
  saving = false,
  as = "span",
  className = "",
  ariaLabel = "Rename",
}: {
  value: string;
  onSave: (next: string) => void;
  saving?: boolean;
  as?: ElementType;
  className?: string;
  ariaLabel?: string;
}) {
  const Tag = as;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!editing) setDraft(value);
  }, [value, editing]);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  const commit = () => {
    const next = draft.trim();
    setEditing(false);
    if (next && next !== value) onSave(next);
    else setDraft(value);
  };

  if (editing) {
    return (
      <input
        ref={inputRef}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            commit();
          } else if (event.key === "Escape") {
            setDraft(value);
            setEditing(false);
          }
        }}
        className={`w-full rounded-lg border border-primary/40 bg-white px-2 py-1 outline-none ring-4 ring-primary/10 ${className}`}
      />
    );
  }

  return (
    <span className="group/title inline-flex min-w-0 max-w-full items-center gap-2">
      <Tag className={`min-w-0 truncate ${className}`}>{value}</Tag>
      {saving ? (
        <Spinner className="text-gray-400" />
      ) : (
        <button
          type="button"
          onClick={() => setEditing(true)}
          aria-label={ariaLabel}
          className="shrink-0 rounded-md p-1 text-gray-300 opacity-0 transition-all hover:bg-gray-100 hover:text-primary group-hover/title:opacity-100"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 20h9" />
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
          </svg>
        </button>
      )}
    </span>
  );
}
