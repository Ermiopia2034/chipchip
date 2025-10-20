"use client";

import React, { useMemo, useState } from "react";
import { useChat } from "@/lib/chatStore";

export default function ChatHistoryMenu() {
  const { threads, openThread, sessionId } = useChat();
  const [open, setOpen] = useState(false);
  const items = useMemo(() => {
    return [...threads].sort((a, b) => b.updatedAt - a.updatedAt).slice(0, 20);
  }, [threads]);

  return (
    <div className="relative inline-block text-left">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="rounded-xl border border-black/10 dark:border-white/15 bg-white/60 dark:bg-white/5 px-3 py-1.5 text-xs hover:bg-white/80 transition-colors"
      >
        Chats
      </button>
      {open ? (
        <div className="absolute right-0 mt-2 w-64 rounded-xl border border-black/10 dark:border-white/15 bg-white/90 dark:bg-gray-900/90 shadow-lg backdrop-blur-sm z-20">
          <div className="max-h-72 overflow-auto pretty-scroll divide-y divide-black/5 dark:divide-white/10">
            {items.length === 0 ? (
              <div className="p-3 text-xs text-gray-500">No previous chats</div>
            ) : (
              items.map((t) => (
                <button
                  key={t.id}
                  onClick={() => {
                    openThread(t.id);
                    setOpen(false);
                  }}
                  className={`w-full text-left p-3 text-xs hover:bg-black/5 dark:hover:bg-white/10 ${
                    t.id === sessionId ? "bg-black/5 dark:bg-white/10" : ""
                  }`}
                >
                  <div className="font-medium truncate">{t.title || "New chat"}</div>
                  <div className="text-[10px] text-gray-500 flex items-center gap-1">
                    <span>#{t.id.slice(0, 8)}</span>
                    <span>•</span>
                    <time dateTime={new Date(t.updatedAt).toISOString()}>
                      {new Date(t.updatedAt).toLocaleString()}
                    </time>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

