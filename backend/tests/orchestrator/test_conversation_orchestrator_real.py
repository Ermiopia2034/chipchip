import os
import pytest


pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
async def test_conversation_orchestrator_basic_reply():
    from app.orchestrator.session_manager import SessionManager
    from app.orchestrator.conversation import ConversationOrchestrator

    sm = SessionManager()
    sid = await sm.create_session()

    orch = ConversationOrchestrator()
    res = await orch.process_message(sid, "How should I store ripe avocados?")
    assert res["type"] == "text"
    assert isinstance(res.get("content"), str)
    assert len(res.get("content")) > 0

