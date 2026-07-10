"use client";

import { useState } from "react";

type AiMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type AiSidebarProps = {
  messages: AiMessage[];
  isSubmitting: boolean;
  error: string;
  onSendPrompt: (prompt: string) => Promise<void>;
};

export const AiSidebar = ({
  messages,
  isSubmitting,
  error,
  onSendPrompt,
}: AiSidebarProps) => {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextPrompt = prompt.trim();
    if (!nextPrompt || isSubmitting) {
      return;
    }

    setPrompt("");
    await onSendPrompt(nextPrompt);
  };

  return (
    <aside className="rounded-[28px] border border-[var(--stroke)] bg-white/85 p-5 shadow-[var(--shadow)] backdrop-blur lg:sticky lg:top-8 lg:h-[calc(100vh-6rem)] lg:self-start">
      <div className="flex h-full flex-col">
        <div className="mb-4">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--gray-text)]">
            AI Assistant
          </p>
          <h2 className="mt-2 font-display text-2xl font-semibold text-[var(--navy-dark)]">
            Board Co-Pilot
          </h2>
          <p className="mt-2 text-sm text-[var(--gray-text)]">
            Ask for create, edit, move, delete, or rename actions.
          </p>
        </div>

        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto rounded-2xl border border-[var(--stroke)] bg-[var(--surface)]/70 p-3">
          {messages.length === 0 ? (
            <p className="text-sm text-[var(--gray-text)]">
              Try: Rename Backlog to Ideas and add a planning card.
            </p>
          ) : null}
          {messages.map((message) => {
            const isUser = message.role === "user";
            return (
              <article
                key={message.id}
                className={[
                  "rounded-2xl px-3 py-2 text-sm leading-6",
                  isUser
                    ? "ml-8 bg-[var(--primary-blue)]/15 text-[var(--navy-dark)]"
                    : "mr-8 bg-white text-[var(--navy-dark)]",
                ].join(" ")}
              >
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                  {isUser ? "You" : "Assistant"}
                </p>
                <p>{message.content}</p>
              </article>
            );
          })}
        </div>

        {error ? (
          <p className="mt-3 text-sm font-semibold text-red-600" role="alert">
            {error}
          </p>
        ) : null}

        <form className="mt-4 flex flex-col gap-3" onSubmit={handleSubmit}>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Ask AI to update this board"
            className="min-h-24 resize-y rounded-2xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm outline-none ring-offset-2 transition focus:ring-2 focus:ring-[var(--primary-blue)]"
            disabled={isSubmitting}
          />
          <button
            type="submit"
            className="rounded-2xl bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Thinking..." : "Send to AI"}
          </button>
        </form>
      </div>
    </aside>
  );
};
