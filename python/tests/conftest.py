import asyncio

import pytest


@pytest.fixture(autouse=True)
def close_pytest_asyncio_fallback_loop():
    """Close pytest-asyncio's fallback loop before -W error unraisable checks."""
    yield
    policy = asyncio.get_event_loop_policy()
    try:
        loop = policy.get_event_loop()
    except RuntimeError:
        return
    if not loop.is_closed():
        loop.close()
    policy.set_event_loop(None)
