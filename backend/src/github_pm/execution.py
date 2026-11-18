"""Execute complete blocking operations outside the ASGI event loop.

Generated-by: Codex
"""

from functools import wraps
import inspect
from typing import get_type_hints

from starlette.concurrency import run_in_threadpool


def offload(function):
    """Keep routes awaitable while offloading synchronous HTTP and backoff."""

    @wraps(function)
    async def run(*args, **kwargs):
        return await run_in_threadpool(function, *args, **kwargs)

    # FastAPI resolves annotations in the wrapper's module. Resolve postponed
    # annotations here, where the original function's globals are available.
    run.__annotations__ = get_type_hints(function, include_extras=True)
    run.__signature__ = inspect.signature(function, eval_str=True)
    return run
