import asyncio
import pytest


pytestmark = pytest.mark.asyncio


class FakeSessionManager:
    def __init__(self):
        self.store = {}
        self.ttl = 60
        self.max_history = 10

    async def create_session(self):
        sid = "sid-1"
        self.store[f"session:{sid}"] = {
            "session_id": sid,
            "user_type": "customer",
            "registered": True,
            "name": "Tester",
            "context": {"current_flow": "idle", "awaiting_confirmation": False},
            "conversation_history": [],
        }
        return sid

    async def get_session(self, session_id: str):
        return self.store.get(f"session:{session_id}")

    async def update_session(self, session_id: str, updates):
        data = self.store.get(f"session:{session_id}")
        if not data:
            data = {"session_id": session_id, "conversation_history": [], "context": {}}
            self.store[f"session:{session_id}"] = data
        data.update(updates)

    async def add_message(self, session_id: str, role: str, content: str):
        data = self.store.get(f"session:{session_id}")
        if not data:
            data = {"session_id": session_id, "conversation_history": [], "context": {}}
            self.store[f"session:{session_id}"] = data
        data.setdefault("conversation_history", []).append({"role": role, "content": content})


class FakeIntentDetector:
    def detect(self, text: str):
        return {"intent": "product_inquiry", "entities": {}}


class FakeLLMService:
    def __init__(self):
        self.calls = 0

    def chat(self, messages, tools=None):  # noqa: D401
        # First call → tool call; second call → final text
        self.calls += 1
        if self.calls == 1:
            return {"type": "tool_call", "name": "search_products", "arguments": {"query": "tomato"}}
        return {"type": "text", "content": "Here you go!"}


class FakeToolRegistry:
    async def execute(self, name: str, args, session_id=None):
        assert name == "search_products"
        assert "query" in args
        return {"success": True, "data": [{"product_name": "Tomatoes"}], "message": "Found 1 product"}


async def test_orchestrator_tool_followup(monkeypatch):
    # Patch classes inside the conversation module
    import importlib
    convo_mod = importlib.import_module("app.orchestrator.conversation")

    monkeypatch.setattr(convo_mod, "SessionManager", lambda: FakeSessionManager())
    monkeypatch.setattr(convo_mod, "IntentDetector", lambda: FakeIntentDetector())
    monkeypatch.setattr(convo_mod, "LLMService", lambda: FakeLLMService())
    monkeypatch.setattr(convo_mod, "ToolRegistry", lambda: FakeToolRegistry())

    orch = convo_mod.ConversationOrchestrator()

    # Prepare a pre-existing session
    sid = "sid-1"
    await orch.sessions.create_session()

    res = await orch.process_message(sid, "What vegetables are available?")
    assert res["type"] == "text"
    assert res["content"] == "Here you go!"

