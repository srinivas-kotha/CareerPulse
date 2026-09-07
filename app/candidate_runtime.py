"""Explicit candidate service and task ownership; no ambient current profile.

The legacy server is unchanged until its routes and extension are scoped. This
manager can be used by scoped request dependencies without sharing app.state.
"""

import asyncio
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from fastapi import HTTPException, Request
from starlette.datastructures import State

from app.candidates import CandidateContext, CandidateRegistry
from app.browser_pool import BrowserPool
from app.runtime_helpers import bind_runtime_helpers

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CandidateRuntime:
    context: CandidateContext
    state: State = field(default_factory=State)
    _tasks: set[asyncio.Task] = field(default_factory=set, repr=False)

    def __post_init__(self):
        self.state.db = self.context.db
        self.state.bg_db = self.context.bg_db
        self.state.matcher = None
        self.state.tailor = None
        self.state.ai_client = None
        self.state.embedding_client = None
        self.state.scheduler = None
        self.state.closing = False
        self.state.browser_pool = BrowserPool(self.context.candidate.directory / "browser" / "cookies")
        bind_runtime_helpers(self.state)

    @property
    def candidate_id(self) -> str:
        return self.context.candidate.candidate_id

    def start_task(self, operation: Callable[["CandidateRuntime"], Awaitable]):
        """Capture ownership before scheduling; shutdown drains tasks before DB close."""
        if self.state.closing:
            raise RuntimeError("Candidate runtime is closing")
        task = asyncio.create_task(operation(self), name=f"candidate:{self.candidate_id}")
        self._tasks.add(task)
        task.add_done_callback(self._task_done)
        return task

    def _task_done(self, task):
        self._tasks.discard(task)
        # Retrieve failures even when the launching HTTP request has finished.
        # Callers can still await the task to receive the original exception.
        if not task.cancelled():
            error = task.exception()
            if error is not None:
                logger.error("Candidate %s task failed (%s)", self.candidate_id, type(error).__name__)

    async def close(self):
        self.state.closing = True
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.state.browser_pool.shutdown()


class CandidateRuntimeManager:
    """One persistent runtime per candidate, with serialized initialization."""

    def __init__(self, registry: CandidateRegistry):
        self.registry = registry
        self._runtimes: dict[str, CandidateRuntime] = {}
        self._stack = AsyncExitStack()
        self._lock = asyncio.Lock()
        self._closed = False

    async def get(self, candidate_id: str) -> CandidateRuntime:
        async with self._lock:
            if self._closed:
                raise RuntimeError("Candidate runtime manager is closed")
            # Always verify identity and storage, including cached lookups.
            record = self.registry.get(candidate_id)
            if not record.db_path.is_file():
                raise FileNotFoundError(record.db_path)
            if candidate_id not in self._runtimes:
                # Keep failed startup out of the cache and close its connections.
                async with AsyncExitStack() as pending:
                    context = await pending.enter_async_context(self.registry.context(candidate_id))
                    runtime = CandidateRuntime(context)
                    from app.main import _build_ai_client, _init_embedding_client
                    config = await context.db.get_search_config() or {}
                    ai_settings = await context.db.get_ai_settings()
                    # No installation .env key or legacy resume fallback.
                    client = _build_ai_client(ai_settings)
                    await runtime.state.reinit_ai_services(client, config.get("resume_text", ""))
                    runtime.state.embedding_client = await _init_embedding_client(context.db)
                    self._stack.push_async_callback(pending.pop_all().aclose)
                    self._runtimes[candidate_id] = runtime
            return self._runtimes[candidate_id]

    async def close(self):
        async with self._lock:
            self._closed = True
            await asyncio.gather(*(runtime.close() for runtime in self._runtimes.values()))
            await self._stack.aclose()
            self._runtimes.clear()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()


async def require_candidate_runtime(request: Request) -> CandidateRuntime:
    """Dependency for /api/candidates/{candidate_id}/... routes only."""
    candidate_id = request.path_params.get("candidate_id")
    if not candidate_id:
        raise HTTPException(400, "Explicit candidate ID required")
    manager = getattr(request.app.state, "candidate_runtimes", None)
    if manager is None:
        raise HTTPException(503, "Candidate runtime is not enabled")
    try:
        return await manager.get(candidate_id)
    except KeyError:
        raise HTTPException(404, "Candidate not found") from None
    except FileNotFoundError:
        raise HTTPException(409, "Candidate storage missing; recovery required") from None
