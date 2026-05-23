"""Lightweight worker loop that executes queued simulation jobs."""

from __future__ import annotations

import asyncio
import logging
import signal

from fgc_flow_api.services import JobWorker

logger = logging.getLogger("fgc_flow_api.worker")


async def _run_worker_loop(worker: JobWorker) -> None:
    while True:
        try:
            await worker.run_once()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - operational logging
            logger.exception("Job worker cycle failed: %s", exc)
        await asyncio.sleep(1.0)


async def _wait_for_shutdown(shutdown_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_event.set)
    await shutdown_event.wait()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[fgc-flow-worker] %(asctime)s %(message)s")
    worker = JobWorker()
    shutdown_event = asyncio.Event()
    task = asyncio.create_task(_run_worker_loop(worker))
    await _wait_for_shutdown(shutdown_event)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Worker shut down")


if __name__ == "__main__":
    asyncio.run(main())
