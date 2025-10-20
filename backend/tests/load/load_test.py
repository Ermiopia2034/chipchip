import os
import time
import statistics
import asyncio

import pytest


pytestmark = pytest.mark.asyncio


async def test_concurrent_sessions_message_latency():
    """
    Lightweight concurrency/load probe.

    Modes (via LOAD_MODE):
      - orchestrator: full LLM+RAG path (slow, requires GEMINI_API_KEY)
      - db_search (default): DB-only product search via ToolRegistry (fast)

    Env overrides:
      LOAD_SESSIONS: number of concurrent sessions (default 5)
      LOAD_MSGS: messages per session (default 5)
      LOAD_MAX_P50 / LOAD_MAX_P95: thresholds in seconds (mode-specific defaults)
    """
    from app.orchestrator.session_manager import SessionManager

    mode = os.getenv("LOAD_MODE", "db_search").lower()
    sessions_n = int(os.getenv("LOAD_SESSIONS", "5"))
    msgs_per = int(os.getenv("LOAD_MSGS", "5"))

    # Skip if orchestrator mode requires LLM and key missing
    if mode == "orchestrator" and not os.getenv("GEMINI_API_KEY"):
        pytest.skip("orchestrator mode requires GEMINI_API_KEY")

    sm = SessionManager()
    latencies_all: list[float] = []

    if mode == "orchestrator":
        from app.orchestrator.conversation import ConversationOrchestrator

        orch = ConversationOrchestrator(sessions=sm)

        async def run_session(idx: int) -> list[float]:
            sid = await sm.create_session()
            latencies: list[float] = []
            for j in range(msgs_per):
                t0 = time.perf_counter()
                _ = await orch.process_message(sid, f"Hello {idx}-{j}. How to store tomatoes?")
                latencies.append(time.perf_counter() - t0)
            return latencies

    else:  # db_search default
        from app.orchestrator.tool_registry import ToolRegistry

        tools = ToolRegistry()

        async def run_session(idx: int) -> list[float]:
            sid = await sm.create_session()
            latencies: list[float] = []
            for j in range(msgs_per):
                t0 = time.perf_counter()
                _ = await tools.search_products_handler({"query": "tomato"}, session_id=sid)
                latencies.append(time.perf_counter() - t0)
            return latencies

    tasks = [asyncio.create_task(run_session(i)) for i in range(sessions_n)]
    results = await asyncio.gather(*tasks)
    lats = [x for sub in results for x in sub if isinstance(x, (int, float))]
    assert lats, "No latencies recorded"

    p50 = statistics.median(lats)
    p95 = sorted(lats)[max(0, int(0.95 * len(lats)) - 1)]

    # Thresholds per mode (overridable via env)
    if mode == "orchestrator":
        max_p50 = float(os.getenv("LOAD_MAX_P50", "120"))
        max_p95 = float(os.getenv("LOAD_MAX_P95", "180"))
    else:
        max_p50 = float(os.getenv("LOAD_MAX_P50", "1.0"))
        max_p95 = float(os.getenv("LOAD_MAX_P95", "2.0"))

    assert p50 < max_p50, f"p50 too high: {p50:.2f}s (mode={mode})"
    assert p95 < max_p95, f"p95 too high: {p95:.2f}s (mode={mode})"
