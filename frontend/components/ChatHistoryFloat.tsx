"use client";

import React, { useMemo, useState } from "react";
import { useChat } from "@/lib/chatStore";
import { Plus, History } from "lucide-react";

export default function ChatHistoryFloat() {
  const { threads, openThread, newThread, sessionId } = useChat();
  const [mobileOpen, setMobileOpen] = useState(false);

  const items = useMemo(() => {
    return [...threads].sort((a, b) => b.updatedAt - a.updatedAt).slice(0, 30);
  }, [threads]);

  return (
    <>
      {/* Desktop floating list */}
      <aside className="hidden sm:block fixed left-3 top-24 w-64 max-h-[70vh] z-30">
        <div className="rounded-2xl border border-black/10 dark:border-white/15 bg-white/30 dark:bg-white/5 backdrop-blur-md shadow-lg p-2">
          <div className="flex items-center justify-between px-1 pb-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-gray-800 dark:text-gray-200">
              <History className="h-3.5 w-3.5" />
              Chats
            </div>
            <button
              aria-label="New chat"
              className="inline-flex items-center justify-center h-7 w-7 rounded-xl bg-blue-600 text-white hover:brightness-105 active:brightness-95 btn-glow"
              onClick={() => newThread()}
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
          <div className="overflow-auto max-h-[60vh] pretty-scroll divide-y divide-black/5 dark:divide-white/10">
            {items.length === 0 ? (
              <div className="p-3 text-xs text-gray-600 dark:text-gray-400">No previous chats</div>
            ) : (
              items.map((t) => {
                const active = t.id === sessionId;
                return (
                  <button
                    key={t.id}
                    onClick={() => openThread(t.id)}
                    className={`w-full text-left p-3 text-xs transition rounded-xl my-1 border
                      ${
                        active
                          ? "bg-blue-600/15 dark:bg-blue-500/15 ring-1 ring-blue-500/40 border-transparent"
                          : "bg-white/50 dark:bg-white/5 hover:bg-white/70 dark:hover:bg-white/10 border-black/10 dark:border-white/10"
                      }
                      focus:outline-none focus:ring-2 focus:ring-blue-500/50`}
                  >
                    <div className="font-medium truncate text-gray-900 dark:text-gray-100">{t.title || "New chat"}</div>
                    <div className="text-[10px] text-gray-600 dark:text-gray-400 flex items-center gap-1">
                      <span>#{t.id.slice(0, 8)}</span>
                      <span>•</span>
                      <time dateTime={new Date(t.updatedAt).toISOString()}>
                        {new Date(t.updatedAt).toLocaleString()}
                      </time>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      </aside>

      {/* Mobile floating toggle button */}
      <button
        type="button"
        aria-label={mobileOpen ? "Close chat history" : "Open chat history"}
        className="sm:hidden fixed bottom-6 left-6 z-40 h-12 w-12 rounded-full bg-blue-600 text-white shadow-lg btn-glow"
        onClick={() => setMobileOpen((v) => !v)}
      >
        <History className="h-5 w-5 m-auto" />
      </button>

      {/* Mobile overlay panel */}
      {mobileOpen ? (
        <>
          <div
            className="sm:hidden fixed inset-0 z-40 bg-black/40"
            onClick={() => setMobileOpen(false)}
          />
          <div className="sm:hidden fixed left-4 right-4 bottom-20 max-h-[65vh] z-40 rounded-2xl border border-black/10 dark:border-white/15 bg-white/90 dark:bg-gray-900/90 backdrop-blur-md shadow-2xl p-2">
            <div className="flex items-center justify-between px-1 pb-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-gray-800 dark:text-gray-200">
                <History className="h-3.5 w-3.5" />
                Chats
              </div>
              <button
                aria-label="New chat"
                className="inline-flex items-center justify-center h-7 w-7 rounded-xl bg-blue-600 text-white hover:brightness-105 active:brightness-95 btn-glow"
                onClick={() => {
                  newThread();
                  setMobileOpen(false);
                }}
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
            <div className="overflow-auto max-h-[52vh] pretty-scroll divide-y divide-black/5 dark:divide-white/10">
              {items.length === 0 ? (
                <div className="p-3 text-xs text-gray-700 dark:text-gray-400">No previous chats</div>
              ) : (
                items.map((t) => {
                  const active = t.id === sessionId;
                  return (
                    <button
                      key={t.id}
                      onClick={() => {
                        openThread(t.id);
                        setMobileOpen(false);
                      }}
                      className={`w-full text-left p-3 text-xs transition rounded-xl my-1 border
                        ${
                          active
                            ? "bg-blue-600/15 dark:bg-blue-500/15 ring-1 ring-blue-500/40 border-transparent"
                            : "bg-white/70 dark:bg-white/5 hover:bg-white/80 dark:hover:bg-white/10 border-black/10 dark:border-white/10"
                        }
                        focus:outline-none focus:ring-2 focus:ring-blue-500/50`}
                    >
                      <div className="font-medium truncate text-gray-900 dark:text-gray-100">{t.title || "New chat"}</div>
                      <div className="text-[10px] text-gray-600 dark:text-gray-400 flex items-center gap-1">
                        <span>#{t.id.slice(0, 8)}</span>
                        <span>•</span>
                        <time dateTime={new Date(t.updatedAt).toISOString()}>
                          {new Date(t.updatedAt).toLocaleString()}
                        </time>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </>
      ) : null}
    </>
  );
}
