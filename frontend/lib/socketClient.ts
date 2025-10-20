import { io, Socket } from "socket.io-client";

function getBackendUrl(): string {
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    // Use same host, backend on 8005 per compose; fallback localhost
    const host = hostname || "localhost";
    return `${protocol}//${host}:8005`;
  }
  return process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8005";
}

export type ServerToClientEvents = {
  response: (payload: { content?: string; message?: string }) => void;
  typing: (payload: { isTyping: boolean }) => void;
  session: (payload: { sessionId: string }) => void;
  app_error: (payload: { message: string }) => void;
};

export type ClientToServerEvents = {
  message: (payload: { sessionId?: string; text: string }) => void;
  typing: (payload: { isTyping: boolean }) => void;
};

export type SocketClient = Socket<ServerToClientEvents, ClientToServerEvents>;

export function createSocket(): SocketClient {
  const socket: SocketClient = io(getBackendUrl(), {
    path: "/socket.io",
    transports: ["websocket"],
    withCredentials: true,
  });
  return socket;
}

export async function createSessionId(): Promise<string> {
  const res = await fetch(`${getBackendUrl()}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("Failed to create session");
  const data = await res.json();
  return data.session_id || data.sessionId;
}
