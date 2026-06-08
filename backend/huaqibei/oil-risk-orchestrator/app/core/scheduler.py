"""Scheduler seam for future periodic intelligence ingestion.

M1 uses import-safe no-op scheduling so tests and demos do not require Celery,
APScheduler, Redis, a broker, or worker processes. The ``APSchedulerStub`` can
wrap a real scheduler instance later while preserving the same small method
surface: ``add_job``, ``remove_job``, ``start``, and ``shutdown``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol
from uuid import uuid4


class Scheduler(Protocol):
    """Minimal scheduler contract used by ingestion orchestration code."""

    def add_job(
        self,
        func: Callable[..., object],
        trigger: str | None = None,
        *args: object,
        job_id: str | None = None,
        **kwargs: object,
    ) -> str:
        """Register a future job and return its scheduler job ID."""
        ...

    def remove_job(self, job_id: str) -> None:
        """Remove a registered job if present."""
        ...

    def start(self) -> None:
        """Start scheduling jobs."""
        ...

    def shutdown(self) -> None:
        """Stop scheduling jobs and release scheduler resources."""
        ...


class APSchedulerJob(Protocol):
    """Small protocol for the job object returned by APScheduler."""

    id: str


class APSchedulerLike(Protocol):
    """Optional APScheduler-compatible object accepted by ``APSchedulerStub``."""

    def add_job(
        self,
        func: Callable[..., object],
        trigger: str | None = None,
        *args: object,
        id: str | None = None,
        **kwargs: object,
    ) -> APSchedulerJob:
        """Add a job to a real scheduler and return its job handle."""
        ...

    def remove_job(self, job_id: str) -> None:
        """Remove a job from a real scheduler."""
        ...

    def start(self) -> None:
        """Start a real scheduler."""
        ...

    def shutdown(self) -> None:
        """Shutdown a real scheduler."""
        ...


@dataclass(frozen=True)
class ScheduledJob:
    """Recorded no-op job metadata for tests and future migration."""

    job_id: str
    func: Callable[..., object]
    trigger: str | None = None
    args: tuple[object, ...] = ()
    kwargs: dict[str, object] = field(default_factory=dict)


class NoOpScheduler:
    """In-memory scheduler seam that records jobs but never runs them."""

    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}
        self._started: bool = False

    @property
    def jobs(self) -> tuple[ScheduledJob, ...]:
        """Return registered no-op jobs for diagnostics or tests."""
        return tuple(self._jobs.values())

    @property
    def started(self) -> bool:
        """Return whether ``start`` has been called."""
        return self._started

    def add_job(
        self,
        func: Callable[..., object],
        trigger: str | None = None,
        *args: object,
        job_id: str | None = None,
        **kwargs: object,
    ) -> str:
        """Record a job definition without executing it."""
        resolved_job_id = job_id or f"noop_{uuid4().hex}"
        self._jobs[resolved_job_id] = ScheduledJob(
            job_id=resolved_job_id,
            func=func,
            trigger=trigger,
            args=args,
            kwargs=dict(kwargs),
        )
        return resolved_job_id

    def remove_job(self, job_id: str) -> None:
        """Remove a recorded job; missing IDs are ignored for no-op safety."""
        _ = self._jobs.pop(job_id, None)

    def start(self) -> None:
        """Mark the no-op scheduler as started without launching workers."""
        self._started = True

    def shutdown(self) -> None:
        """Mark the no-op scheduler as stopped without external side effects."""
        self._started = False


class APSchedulerStub:
    """Thin adapter shape for future APScheduler integration.

    Pass a configured APScheduler instance later to delegate calls. Without one,
    this class remains importable and raises clear M1 messages for operations
    that would otherwise require the optional dependency.
    """

    def __init__(self, scheduler: APSchedulerLike | None = None) -> None:
        self._scheduler: APSchedulerLike | None = scheduler

    @property
    def provider_status(self) -> str:
        """Return scheduler adapter identity for diagnostics."""
        return "apscheduler_stub"

    def add_job(
        self,
        func: Callable[..., object],
        trigger: str | None = None,
        *args: object,
        job_id: str | None = None,
        **kwargs: object,
    ) -> str:
        """Delegate to a real APScheduler instance when configured."""
        if self._scheduler is None:
            raise NotImplementedError(
                "APScheduler integration is not configured for M1; use NoOpScheduler "
                + "or inject a configured APScheduler instance."
            )
        job = self._scheduler.add_job(func, trigger, args=args, id=job_id, **kwargs)
        return str(job.id)

    def remove_job(self, job_id: str) -> None:
        """Delegate job removal when a real scheduler is configured."""
        if self._scheduler is None:
            raise NotImplementedError(
                "APScheduler integration is not configured for M1; use NoOpScheduler "
                + "or inject a configured APScheduler instance."
            )
        self._scheduler.remove_job(job_id)

    def start(self) -> None:
        """Delegate scheduler start when configured."""
        if self._scheduler is None:
            raise NotImplementedError(
                "APScheduler integration is not configured for M1; use NoOpScheduler "
                + "or inject a configured APScheduler instance."
            )
        self._scheduler.start()

    def shutdown(self) -> None:
        """Delegate scheduler shutdown when configured."""
        if self._scheduler is None:
            raise NotImplementedError(
                "APScheduler integration is not configured for M1; use NoOpScheduler "
                + "or inject a configured APScheduler instance."
            )
        self._scheduler.shutdown()


class CelerySchedulerStub(NoOpScheduler):
    """No-op placeholder for a future Celery beat ingestion scheduler."""

    @property
    def provider_status(self) -> str:
        """Return scheduler adapter identity for diagnostics."""
        return "celery_stub"


default_scheduler: Scheduler = NoOpScheduler()

__all__ = [
    "APSchedulerStub",
    "CelerySchedulerStub",
    "NoOpScheduler",
    "ScheduledJob",
    "Scheduler",
    "default_scheduler",
]
