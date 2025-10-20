"use client";

import React, { useCallback, useState } from "react";
import { useChat } from "@/lib/chatStore";
import { Send } from "lucide-react";

export default function ChatInput() {
  const { sendMessage, isTyping } = useChat();
  const [text, setText] = useState("");

  const onSend = useCallback(() => {
    const t = text.trim();
    if (!t) return;
    sendMessage(t);
    setText("");
  }, [sendMessage, text]);

  return (
    <div className="w-full">
      <div className="relative flex items-end gap-2 rounded-2xl border border-black/10 dark:border-white/10 glass p-2">
        <textarea
          className="flex-1 bg-transparent resize-none outline-none px-2 py-2 text-sm max-h-40"
          placeholder={isTyping ? "Assistant is typing..." : "Type your message…"}
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          maxLength={1000}
        />
        <button
          aria-label="Send message"
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 text-white px-4 py-2 text-sm font-medium btn-glow disabled:opacity-60 disabled:cursor-not-allowed"
          onClick={onSend}
          disabled={!text.trim()}
          title="Send (Enter)"
        >
          <Send className="h-4 w-4" />
          <span className="hidden sm:inline">Send</span>
        </button>
      </div>
      <div className="mt-1 text-[10px] text-gray-500">Press Enter to send • Shift+Enter for newline</div>
    </div>
  );
}
