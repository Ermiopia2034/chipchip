"use client";

import React, { useEffect, useMemo, useRef } from "react";
import { ChatProvider, useChat } from "@/lib/chatStore";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import TypingIndicator from "@/components/TypingIndicator";
import QuickActionsBar from "@/components/QuickActionsBar";
import ChatHistoryFloat from "@/components/ChatHistoryFloat";
import Link from "next/link";
import type { ChatMessage as ChatMsg } from "@/lib/chatStore";

function ChatView() {
  const { messages, isTyping, isConnected, sessionId, newThread } = useChat();
  const listRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom on new message
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, isTyping]);

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
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => newThread()}
          className="rounded-xl border border-black/10 dark:border-white/15 bg-white/60 dark:bg-white/5 px-3 py-1.5 text-xs hover:bg-white/80 transition-colors"
        >
          New Chat
        </button>
      </div>
    </div>
  ), [isConnected, sessionId, newThread]);

  return (
    <div className="fixed inset-0 px-2 sm:px-6 py-4 overflow-hidden">
      <ChatHistoryFloat />
      {/* Decorative gradients for chat page */}
      <div className="pointer-events-none absolute -top-24 -left-24 h-[360px] w-[360px] rounded-full bg-[radial-gradient(circle_at_center,hsl(var(--brand)/0.18)_0%,transparent_60%)] float-slow" />
      <div className="pointer-events-none absolute -bottom-24 -right-24 h-[420px] w-[420px] rounded-full bg-[radial-gradient(circle_at_center,hsl(var(--brand-2)/0.18)_0%,transparent_60%)] float-slow float-delay" />
      <div className="mx-auto w-full max-w-3xl h-full rounded-2xl glass border border-black/10 dark:border-white/10 shadow-lg flex flex-col overflow-hidden">
        {header}
        <div ref={listRef} className="flex-1 min-h-0 overflow-y-auto py-4 px-3 sm:px-4 bg-grid chat-scroll pretty-scroll">
          {messages.map((m, i) => (
            <ChatMessage key={i} message={m} />
          ))}
          <TypingIndicator visible={isTyping} />
        </div>
        <div className="px-3 sm:px-4 pb-4">
          <div className="mb-3">
            <QuickActionsBar />
          </div>
          <ChatInput />
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <ChatProvider>
      <ActionBridge>
        <ChatView />
      </ActionBridge>
    </ChatProvider>
  );
}

function ActionBridge({ children }: { children: React.ReactNode }) {
  const { sendMessage } = useChat();
  useEffect(() => {
    type ActionDetail = { id: "use_recommended" | "set_custom" | "run_flash_sale"; message: ChatMsg };
    type PriceData = { product?: string | null; rows?: unknown[]; recommended?: number | null };
    const asPriceData = (m?: ChatMsg | null): PriceData | null => {
      if (!m) return null;
      if (m.kind !== "prices") return null;
      const d = m.data;
      return d && typeof d === "object" ? (d as PriceData) : null;
    };
    const handler = (ev: Event) => {
      const e = ev as CustomEvent<ActionDetail>;
      const id = e?.detail?.id;
      const source = e?.detail?.message;
      if (!id) return;
      if (id === "use_recommended") {
        const d = asPriceData(source);
        const rec = d?.recommended ?? null;
        const product = d?.product ?? null;
        const txt = rec && product ? `Set ${product} price to ${rec} ETB/kg` : "Use recommended price";
        sendMessage(txt);
      } else if (id === "set_custom") {
        const d = asPriceData(source);
        const product = d?.product ?? "this product";
        sendMessage(`I want to set a custom price for ${product}`);
      } else if (id === "run_flash_sale") {
        sendMessage("Yes, run the suggested flash sale to clear expiring stock");
      }
    };
    window.addEventListener("cc-action", handler as EventListener);
    return () => window.removeEventListener("cc-action", handler as EventListener);
  }, [sendMessage]);
  return <>{children}</>;
}
