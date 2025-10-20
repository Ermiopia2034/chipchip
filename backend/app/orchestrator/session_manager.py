from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from redis import asyncio as aioredis

from app.config import settings


class SessionManager:
    def __init__(self):
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True, max_connections=50)
        self.ttl = int(settings.SESSION_TTL)
        self.max_history = int(settings.MAX_CONVERSATION_HISTORY)

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        data = {
            "session_id": session_id,
            "user_id": None,
            "user_type": "unknown",
            "registered": False,
            "phone": None,
            "name": None,
            "default_location": None,
            "context": {
                "current_flow": "idle",
                "pending_order": None,
                "pending_inventory": None,
                "last_intent": None,
                "awaiting_confirmation": False,
            },
            "conversation_history": [],
            "language": "auto",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "last_active": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        await self.redis.setex(f"session:{session_id}", self.ttl, json.dumps(data))
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        raw = await self.redis.get(f"session:{session_id}")
        if not raw:
            return None
        await self.redis.expire(f"session:{session_id}", self.ttl)
        return json.loads(raw)

    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        data = await self.get_session(session_id) or {}
        # shallow merge for top-level; nested callers should handle deep merge as needed
        data.update(updates)
        data["last_active"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        await self.redis.setex(f"session:{session_id}", self.ttl, json.dumps(data))

    async def add_message(self, session_id: str, role: str, content: str) -> None:
        data = await self.get_session(session_id) or {}
        hist = data.get("conversation_history", [])
        hist.append({"role": role, "content": content, "timestamp": time.time()})
        # Trim to recent N
        if len(hist) > self.max_history:
            hist = hist[-self.max_history :]
        data["conversation_history"] = hist
        data["last_active"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        await self.redis.setex(f"session:{session_id}", self.ttl, json.dumps(data))

    async def get_conversation_context(self, session_id: str, n_messages: int = 10) -> List[Dict[str, str]]:
        data = await self.get_session(session_id)
        if not data:
            return []
        hist = data.get("conversation_history", [])
        return hist[-n_messages:]

