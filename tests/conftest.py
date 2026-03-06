import os
import sys
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from dotenv import dotenv_values  # pip install python-dotenv


# --------------------------------------------------------------------------------------
# NEW: Stabilize asyncio on Windows during pytest teardown.
# This prevents "Windows fatal exception: access violation" in proactor_events.py
# by avoiding ProactorEventLoop + ensuring clean event loop shutdown.
# --------------------------------------------------------------------------------------
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        # If policy can't be set for some reason, continue; event_loop fixture below
        # still does explicit cleanup.
        pass


# --------------------------------------------------------------------------------------
# Load backend .env when running pytest directly (so live AI tests have API key)
# This mimics what your run_tests.py does.
# --------------------------------------------------------------------------------------
BACKEND_ROOT = Path(__file__).resolve().parents[1]  # nuitri_pilot_backend/
ENV_PATH = BACKEND_ROOT / ".env"

if ENV_PATH.exists():
    values = dotenv_values(ENV_PATH)
    for k, v in values.items():
        if v is not None and k not in os.environ:
            os.environ[k] = v

# Normalize key names so BOTH AIClient and OpenAIAgent work
# (Different parts of your codebase read different env var names.)
if "OPENAI_API_KEY" not in os.environ and "OPEN_AI_API_KEY" in os.environ:
    os.environ["OPENAI_API_KEY"] = os.environ["OPEN_AI_API_KEY"]
if "OPEN_AI_API_KEY" not in os.environ and "OPENAI_API_KEY" in os.environ:
    os.environ["OPEN_AI_API_KEY"] = os.environ["OPENAI_API_KEY"]

if "AI_MODEL" not in os.environ and "OPEN_AI_MODEL" in os.environ:
    os.environ["AI_MODEL"] = os.environ["OPEN_AI_MODEL"]
if "OPEN_AI_MODEL" not in os.environ and "AI_MODEL" in os.environ:
    os.environ["OPEN_AI_MODEL"] = os.environ["AI_MODEL"]

# Ensure tests run in test mode unless explicitly overridden
os.environ.setdefault("ENV", "test")


# Import app AFTER env is loaded (important)
from src.main import app  # noqa: E402


# --------------------------------------------------------------------------------------
# NEW: Provide a session-wide event loop and close it cleanly.
# This prevents Windows proactor __del__/GC crashes at interpreter shutdown.
# --------------------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    """
    Dedicated asyncio event loop for the whole test session with explicit cleanup.

    Why:
    - On Windows, leaked async transports/clients can crash Python at shutdown
      (0xC0000005 in asyncio\\proactor_events.py) during garbage collection.
    - This fixture cancels pending tasks and closes the loop deterministically.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    yield loop

    # Best-effort: cancel any pending tasks to avoid __del__ on half-torn-down objects
    try:
        pending = asyncio.all_tasks(loop)
    except Exception:
        pending = set()

    for task in pending:
        task.cancel()

    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

    loop.close()


@pytest.fixture(scope="session")
def is_docker_available() -> bool:
    # Simple check: if Docker isn't running, integration tests will be skipped.
    # (We avoid hard failing your whole suite.)
    try:
        import subprocess
        r = subprocess.run(["docker", "info"], capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False


@pytest.fixture(scope="session")
def testclient():
    """FastAPI test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers():
    """Generate a valid JWT without hitting DB login (fast & stable)."""
    from src.auth.token import create_token
    token = create_token("test-user-123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client(testclient):
    return testclient