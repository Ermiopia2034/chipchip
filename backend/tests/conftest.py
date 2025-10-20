import os
import sys
import asyncio
import pytest
import pytest_asyncio


# Ensure backend package root is on sys.path for `import app.*`
BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


_DB_LOCK = None


async def _get_db_lock():
    global _DB_LOCK
    if _DB_LOCK is None:
        _DB_LOCK = asyncio.Lock()
    return _DB_LOCK


@pytest_asyncio.fixture
async def db_serialized():
    """Serialize DB-heavy integration tests to avoid asyncpg concurrency flaps.

    This fixture yields under a global asyncio.Lock so that tests that perform
    back-to-back DB operations don't overlap on the same underlying connection.
    """
    lock = await _get_db_lock()
    async with lock:
        yield


@pytest.fixture(scope="session")
def event_loop():
    """Provide a single event loop for all tests to avoid cross-loop issues.

    pytest-asyncio in strict mode creates a new loop per test by default. A
    session-scoped loop prevents errors like "Future attached to a different
    loop" and reduces asyncpg connection contention in pooled engines created
    at import time.
    """
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()
