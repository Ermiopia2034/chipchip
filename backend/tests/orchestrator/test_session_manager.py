import asyncio
import os
import pytest


@pytest.mark.asyncio
async def test_session_manager_basics():
    from app.orchestrator.session_manager import SessionManager

    sm = SessionManager()
    sid = await sm.create_session()
    assert sid

    s = await sm.get_session(sid)
    assert s and s["session_id"] == sid

    await sm.add_message(sid, "user", "hello")
    ctx = await sm.get_conversation_context(sid, 1)
    assert ctx and ctx[-1]["content"] == "hello"

