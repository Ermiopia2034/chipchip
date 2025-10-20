"use client";

import React from "react";

export default function TypingIndicator({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <div className="flex items-center gap-2 text-gray-500 text-sm py-2">
      <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white/75 dark:bg-white/5 px-3 py-2">
        <div className="flex gap-1 items-end">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
        </div>
      </div>
      <span className="text-xs">Assistant is typing…</span>
    </div>
  );
}
