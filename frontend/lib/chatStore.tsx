"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { createSessionId, createSocket, SocketClient, ServerToClientEvents, ClientToServerEvents } from "./socketClient";
import { parseAssistantPayload, shouldSimulateCOD, type ParsedKind } from "./messageParser";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  kind?: ParsedKind;
  data?: any;
  actions?: { id: string; label: string }[];
  metadata?: any;
  raw?: any;
};

type ChatState = {
  messages: ChatMessage[];
  sessionId: string | null;
  isConnected: boolean;
  isTyping: boolean;
  language: string;
  backendUrl: string;
};

type ChatActions = {
  sendMessage: (text: string) => void;
  addMessage: (msg: ChatMessage) => void;
  setLanguage: (lang: string) => void;
  clearChat: () => void;
};

const ChatContext = createContext<(ChatState & ChatActions) | null>(null);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  // Language handling intentionally omitted per requirements
  const [language, setLanguage] = useState<string>("auto");
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8005";
  const socketRef = useRef<SocketClient | null>(null);
  const sessionIdRef = useRef<string | null>(null);

  // Keep a live ref of sessionId for event handlers without re-creating effects
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  // Persist and restore session + history
  useEffect(() => {
    if (typeof window === "undefined") return;
    const savedSession = localStorage.getItem("session_id");
    const savedHistory = localStorage.getItem("chat_history");
    if (savedSession) setSessionId(savedSession);
    if (savedHistory) {
      try {
        setMessages(JSON.parse(savedHistory));
      } catch {}
    }
  }, []);

  // Establish session if needed
  useEffect(() => {
    if (sessionId) return;
    let cancelled = false;
    (async () => {
      try {
        const sid = await createSessionId();
        if (cancelled) return;
        setSessionId(sid);
        if (typeof window !== "undefined") localStorage.setItem("session_id", sid);
      } catch (e) {
        console.error("Failed to create session", e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  // Socket lifecycle
  useEffect(() => {
    const socket = createSocket();
    socketRef.current = socket;

    socket.on("connect", () => setIsConnected(true));
    socket.on("disconnect", () => setIsConnected(false));
    socket.on("typing", (p) => setIsTyping(!!p?.isTyping));
    socket.on("session", (p) => {
      if (p?.sessionId && !sessionIdRef.current) {
        setSessionId(p.sessionId);
        if (typeof window !== "undefined") localStorage.setItem("session_id", p.sessionId);
      }
    });
    socket.on("response", (payload: Parameters<ServerToClientEvents["response"]>[0]) => {
      const parsed = parseAssistantPayload(payload);
      if (parsed?.content != null) {
        const msg: ChatMessage = {
          role: "assistant",
          content: String(parsed.content),
          timestamp: Date.now(),
          kind: parsed.kind,
          data: parsed.data,
          actions: parsed.actions,
          metadata: parsed.metadata,
          raw: payload,
        };
        setMessages((m) => {
          const next = [...m, msg];
          if (typeof window !== "undefined") localStorage.setItem("chat_history", JSON.stringify(next));
          return next;
        });

        // Simulate COD processing pause if indicated by content
        if (shouldSimulateCOD(msg.content)) {
          const statusMsg: ChatMessage = {
            role: "assistant",
            content: "Processing Cash on Delivery…",
            kind: "status",
            timestamp: Date.now(),
          };
          setMessages((m) => {
            const next = [...m, statusMsg];
            if (typeof window !== "undefined") localStorage.setItem("chat_history", JSON.stringify(next));
            return next;
          });
          setTimeout(() => {
            const done: ChatMessage = {
              role: "assistant",
              content: "Order Confirmed for COD",
              timestamp: Date.now(),
              kind: "text",
            };
            setMessages((m) => {
              const next = [...m, done];
              if (typeof window !== "undefined") localStorage.setItem("chat_history", JSON.stringify(next));
              return next;
            });
          }, 5000);
        }
      }
    });
    socket.on("app_error", (p) => {
      console.error("Server error", p?.message || p);
    });
    // Also surface transport / connect errors for visibility
    socket.io.on("error", (err: Error) => {
      console.error("Transport error", err);
    });
    socket.io.on("reconnect_error", (err: Error) => {
      console.error("Reconnect error", err);
    });

    return () => {
      try { socket.disconnect(); } catch {}
      socketRef.current = null;
    };
  }, []);

  // Actions
  const addMessage = useCallback((msg: ChatMessage) => {
    setMessages((m) => {
      const next = [...m, msg];
      if (typeof window !== "undefined") localStorage.setItem("chat_history", JSON.stringify(next));
      return next;
    });
  }, []);

  const sendMessage = useCallback((text: string) => {
    if (!text?.trim()) return;
    const msg: ChatMessage = { role: "user", content: text, timestamp: Date.now() };
    addMessage(msg);
    const payload: Parameters<ClientToServerEvents["message"]>[0] = { text };
    if (sessionId) payload.sessionId = sessionId;
    socketRef.current?.emit("message", payload);
  }, [addMessage, sessionId]);

  const clearChat = useCallback(() => {
    setMessages([]);
    if (typeof window !== "undefined") localStorage.removeItem("chat_history");
  }, []);

  const setLang = useCallback((lang: string) => {
    setLanguage(lang);
  }, []);

  const value = useMemo(
    () => ({
      messages,
      sessionId,
      isConnected,
      isTyping,
      language,
      backendUrl,
      sendMessage,
      addMessage,
      setLanguage: setLang,
      clearChat,
    }),
    [messages, sessionId, isConnected, isTyping, language, backendUrl, sendMessage, addMessage, setLang, clearChat]
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used within ChatProvider");
  return ctx;
}
