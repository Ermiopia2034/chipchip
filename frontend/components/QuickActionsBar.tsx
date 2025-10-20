"use client";

import React from "react";
import { useChat, type ChatMessage } from "@/lib/chatStore";
import type { ParsedKind } from "@/lib/messageParser";

const actions = [
  { label: "Register me", text: "I want to register" },
  { label: "Add inventory", text: "I want to add tomatoes" },
  { label: "Pricing insights", text: "Show pricing insights for tomatoes" },
  { label: "What's in season?", text: "What's in season right now?" },
  { label: "Check schedule", text: "Show my schedule for this week" },
];

export default function QuickActionsBar() {
  const { sendMessage, addMessage } = useChat();
  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((a) => (
        <button
          key={a.label}
          className="rounded-full border border-black/10 dark:border-white/15 bg-white/60 dark:bg-white/5 px-3 py-1.5 text-xs hover:bg-white/80 transition-colors"
          onClick={() => {
            sendMessage(a.text);
            // Inject guided forms for key flows
            if (a.label === "Register me") {
              const msg: ChatMessage = {
                role: "assistant",
                content: "Let’s get you registered.",
                kind: "registration_form" as ParsedKind,
                timestamp: Date.now(),
              };
              addMessage(msg);
            } else if (a.label === "Add inventory") {
              const msg: ChatMessage = {
                role: "assistant",
                content: "Let’s add your product.",
                kind: "add_inventory_form" as ParsedKind,
                timestamp: Date.now(),
              };
              addMessage(msg);
            }
          }}
        >
          {a.label}
        </button>
      ))}
    </div>
  );
}
