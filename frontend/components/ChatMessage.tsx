"use client";

import React from "react";
import { ChatMessage as Msg } from "@/lib/chatStore";
import { User, Sprout } from "lucide-react";

export default function ChatMessage({ message }: { message: Msg }) {
  const isUser = message.role === "user";
  return (
    <div className={`w-full flex ${isUser ? "justify-end" : "justify-start"} my-2 message-in`}>
      <div className={`flex items-end gap-2 max-w-[85%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        {/* Avatar */}
        <div className={`h-8 w-8 rounded-full shrink-0 grid place-items-center ${isUser ? "bg-gradient-to-tr from-blue-600 via-fuchsia-500 to-amber-400 text-white" : "bg-gray-200 text-gray-700 dark:bg-gray-800 dark:text-gray-200"}`}>
          {isUser ? <User className="h-4 w-4" /> : <Sprout className="h-4 w-4" />}
        </div>
        {/* Bubble */}
        <div
          className={`px-3 py-2 rounded-2xl text-[0.92rem] leading-relaxed whitespace-pre-wrap shadow-sm border ${
            isUser
              ? "bg-gradient-to-tr from-blue-600 via-indigo-600 to-fuchsia-600 text-white border-white/10"
              : "bg-white/75 dark:bg-white/5 text-gray-900 dark:text-gray-100 border-black/10 dark:border-white/10"
          }`}
        >
          {message.content}
          <div className={`text-[10px] mt-1 opacity-70 ${isUser ? "text-blue-100" : "text-gray-500"}`}>
            {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </div>
        </div>
      </div>
    </div>
  );
}
