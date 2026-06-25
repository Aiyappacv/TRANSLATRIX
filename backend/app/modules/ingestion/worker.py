from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

logger = logging.getLogger("translatrix.ingestion.worker")


class JobStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job:
    def __init__(
        self,
        job_type: str,
        tenant_id: UUID,
        payload: dict[str, Any],
        handler: Callable[..., Any],
        max_retries: int = 3,
    ):
        self.id = str(uuid4())
        self.job_type = job_type
        self.tenant_id = tenant_id
        self.payload = payload
        self.handler = handler
        self.max_retries = max_retries
        self.retry_count = 0
        self.status = JobStatus.QUEUED
        self.error: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None


class BackgroundWorker:
    def __init__(self, max_concurrency: int = 4):
        self.max_concurrency = max_concurrency
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._active_jobs: dict[str, Job] = {}
        self._completed_jobs: dict[str, Job] = {}
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._running = False
        self._workers: list[asyncio.Task] = []

    async def start(self):
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker_loop(i), name=f"worker-{i}")
            for i in range(self.max_concurrency)
        ]
        logger.info("background_worker_started concurrency=%d", self.max_concurrency)

    async def stop(self, wait: bool = True):
        self._running = False
        for _ in self._workers:
            await self._queue.put(None)
        if wait:
            await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("background_worker_stopped")

    def enqueue(
        self,
        job_type: str,
        tenant_id: UUID,
        payload: dict[str, Any],
        handler: Callable[..., Any],
        max_retries: int = 3,
    ) -> str:
        job = Job(job_type, tenant_id, payload, handler, max_retries)
        self._active_jobs[job.id] = job
        self._queue.put_nowait(job)
        logger.info("job_enqueued id=%s type=%s", job.id, job_type)
        return job.id

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._active_jobs.get(job_id) or self._completed_jobs.get(job_id)

    def get_active_jobs(self, tenant_id: Optional[UUID] = None) -> list[Job]:
        jobs = list(self._active_jobs.values())
        if tenant_id:
            jobs = [j for j in jobs if j.tenant_id == tenant_id]
        return jobs

    def get_batch_progress(self, batch_id: str) -> dict[str, Any]:
        batch_jobs = [
            j for j in self._active_jobs.values()
            if j.payload.get("batch_id") == batch_id
        ]
        completed = [
            j for j in self._completed_jobs.values()
            if j.payload.get("batch_id") == batch_id
        ]
        all_jobs = batch_jobs + completed
        total = len(all_jobs)
        queued = sum(1 for j in all_jobs if j.status == JobStatus.QUEUED)
        processing = sum(1 for j in all_jobs if j.status == JobStatus.PROCESSING)
        failed = sum(1 for j in all_jobs if j.status == JobStatus.FAILED)
        done = sum(1 for j in all_jobs if j.status == JobStatus.COMPLETED)

        return {
            "batch_id": batch_id,
            "total": total,
            "queued": queued,
            "processing": processing,
            "completed": done,
            "failed": failed,
            "jobs": [
                {
                    "job_id": j.id,
                    "job_type": j.job_type,
                    "status": j.status,
                    "payload": j.payload,
                    "error": j.error,
                    "created_at": j.created_at.isoformat(),
                    "started_at": j.started_at.isoformat() if j.started_at else None,
                    "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                }
                for j in all_jobs
            ],
        }

    async def _worker_loop(self, worker_id: int):
        while self._running:
            job = await self._queue.get()
            if job is None:
                self._queue.task_done()
                break
            async with self._semaphore:
                job.status = JobStatus.PROCESSING
                job.started_at = datetime.now(timezone.utc)
                logger.info("job_started id=%s type=%s worker=%d", job.id, job.job_type, worker_id)

                try:
                    if asyncio.iscoroutinefunction(job.handler):
                        await job.handler(**job.payload)
                    else:
                        await asyncio.to_thread(job.handler, **job.payload)

                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.now(timezone.utc)
                    logger.info("job_completed id=%s type=%s", job.id, job.job_type)

                except Exception as exc:
                    job.retry_count += 1
                    logger.warning(
                        "job_failed id=%s type=%s retry=%d/%d error=%s",
                        job.id, job.job_type, job.retry_count, job.max_retries, exc,
                    )

                    if job.retry_count < job.max_retries:
                        job.status = JobStatus.QUEUED
                        await asyncio.sleep(2 ** job.retry_count)
                        await self._queue.put(job)
                    else:
                        job.status = JobStatus.FAILED
                        job.error = str(exc)
                        job.completed_at = datetime.now(timezone.utc)
                        logger.error("job_permanently_failed id=%s type=%s error=%s", job.id, job.job_type, exc)

                finally:
                    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                        self._active_jobs.pop(job.id, None)
                        self._completed_jobs[job.id] = job

            self._queue.task_done()


_DEFAULT_CONCURRENCY = 4

# Default concurrency per named pool. "metadata" handles fast,
# always-runs-on-every-upload jobs (metadata_process, embedding_detect) —
# "extraction" handles slow, long-running jobs (extract_document) whose
# duration can now be minutes for large chunked multi-page documents. Kept
# as two separate pools/queues (each with its own semaphore) so a handful
# of slow extraction jobs can never starve metadata jobs of a worker slot,
# which previously left newly-uploaded documents stuck at "uploaded"
# whenever the single shared 4-slot pool was busy with extractions.
_POOL_CONCURRENCY: dict[str, int] = {
    "metadata": _DEFAULT_CONCURRENCY,
    "extraction": _DEFAULT_CONCURRENCY,
}

_worker_instances: dict[str, BackgroundWorker] = {}
_worker_instances_lock: Optional[asyncio.Lock] = None


def _get_lock() -> asyncio.Lock:
    global _worker_instances_lock
    if _worker_instances_lock is None:
        _worker_instances_lock = asyncio.Lock()
    return _worker_instances_lock


def configure_pool_concurrency(pool: str, concurrency: int) -> None:
    """Set concurrency for a pool before it's first started. Called once at
    app startup from settings — no-op if the pool is already running."""
    if pool not in _worker_instances:
        _POOL_CONCURRENCY[pool] = max(1, concurrency)


async def get_worker(pool: str = "metadata") -> BackgroundWorker:
    """Returns the named worker pool, starting it on first use.

    `pool` defaults to "metadata" (the original single shared pool's
    behavior) for backward compatibility with any caller that doesn't
    specify one explicitly."""
    if pool in _worker_instances:
        return _worker_instances[pool]
    async with _get_lock():
        if pool not in _worker_instances:
            instance = BackgroundWorker(max_concurrency=_POOL_CONCURRENCY.get(pool, _DEFAULT_CONCURRENCY))
            await instance.start()
            _worker_instances[pool] = instance
            logger.info("background_worker_pool_created pool=%s concurrency=%d", pool, instance.max_concurrency)
    return _worker_instances[pool]


async def shutdown_worker():
    """Stops every named worker pool that has been started."""
    global _worker_instances
    instances = list(_worker_instances.items())
    _worker_instances = {}
    for name, instance in instances:
        await instance.stop(wait=True)
        logger.info("background_worker_pool_stopped pool=%s", name)


async def get_all_active_jobs(tenant_id: Optional[UUID] = None) -> list[Job]:
    jobs: list[Job] = []
    for instance in _worker_instances.values():
        jobs.extend(instance.get_active_jobs(tenant_id))
    return jobs


async def get_batch_progress_all_pools(batch_id: str) -> dict[str, Any]:
    """Batch progress can include jobs from more than one pool (e.g. a batch
    that has both metadata and chained embedding jobs), so this aggregates
    across every started pool rather than assuming a single shared queue."""
    total = queued = processing = failed = done = 0
    jobs: list[dict[str, Any]] = []
    for instance in _worker_instances.values():
        progress = instance.get_batch_progress(batch_id)
        total += progress["total"]
        queued += progress["queued"]
        processing += progress["processing"]
        failed += progress["failed"]
        done += progress["completed"]
        jobs.extend(progress["jobs"])
    return {
        "batch_id": batch_id,
        "total": total,
        "queued": queued,
        "processing": processing,
        "completed": done,
        "failed": failed,
        "jobs": jobs,
    }
