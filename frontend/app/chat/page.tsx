"use client";

import React, { useEffect, useMemo, useRef } from "react";
import { ChatProvider, useChat } from "@/lib/chatStore";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import TypingIndicator from "@/components/TypingIndicator";
import LanguageSelector from "@/components/LanguageSelector";
import Link from "next/link";

function ChatView() {
  const { messages, isTyping, isConnected, sessionId } = useChat();
  const listRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom on new message
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const header = useMemo(() => (
    <div className="flex items-center justify-between py-3 px-4 border-b border-black/10 dark:border-white/10">
      <div className="flex items-center gap-3">
        <Link href="/" className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-xl bg-gradient-to-tr from-blue-600 via-fuchsia-500 to-amber-400" />
          <span className="font-semibold tracking-tight hidden sm:block">ChipChip</span>
        </Link>
        <div className="pl-2 border-l border-black/10 dark:border-white/10">
          <div className="font-medium">Horticulture Assistant</div>
          <div className="text-xs text-gray-500 flex items-center gap-2">
            <span className={`inline-flex h-2.5 w-2.5 rounded-full ${isConnected ? "bg-green-500" : "bg-yellow-500"} animate-pulse`} />
            {isConnected ? "Connected" : "Reconnecting..."} • Session {sessionId?.slice(0, 8) || "—"}
          </div>
        </div>
      </div>
      <LanguageSelector />
    </div>
  ), [isConnected, sessionId]);

  return (
    <div className="relative min-h-screen px-2 sm:px-6 py-4">
      <div className="mx-auto w-full max-w-3xl rounded-2xl glass border border-black/10 dark:border-white/10 shadow-lg">
        {header}
        <div ref={listRef} className="flex-1 overflow-y-auto py-4 px-3 sm:px-4" style={{ maxHeight: "calc(100dvh - 200px)" }}>
          {messages.map((m, i) => (
            <ChatMessage key={i} message={m} />
          ))}
          <TypingIndicator visible={isTyping} />
        </div>
        <div className="px-3 sm:px-4 pb-4">
          <ChatInput />
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <ChatProvider>
      <ChatView />
    </ChatProvider>
  );
}
