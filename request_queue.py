"""In-process request queue for serializing outbound TikTok API calls."""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass
from queue import Empty, Full, Queue
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class QueueFullError(Exception):
    pass


class QueueTimeoutError(Exception):
    pass


@dataclass
class _Job:
    fn: Callable[[], Any]
    future: Future[Any]


class RequestQueue:
    def __init__(
        self,
        *,
        workers: int = 1,
        max_size: int = 100,
        min_interval: float = 0.5,
        default_timeout: float = 120.0,
    ) -> None:
        self._max_size = max_size
        self._queue: Queue[_Job] = Queue(maxsize=max_size)
        self._min_interval = min_interval
        self._default_timeout = default_timeout
        self._rate_lock = threading.Lock()
        self._stats_lock = threading.Lock()
        self._last_started = 0.0
        self._active = 0
        self._completed = 0
        self._workers = workers
        self._threads: list[threading.Thread] = []
        self._shutdown = threading.Event()

    def start(self) -> None:
        if self._threads:
            return

        for index in range(self._workers):
            thread = threading.Thread(
                target=self._worker,
                name=f"request-queue-{index}",
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)

    def _wait_for_slot(self) -> None:
        with self._rate_lock:
            elapsed = time.monotonic() - self._last_started
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_started = time.monotonic()

    def _worker(self) -> None:
        while not self._shutdown.is_set():
            try:
                job = self._queue.get(timeout=0.5)
            except Empty:
                continue

            try:
                self._wait_for_slot()
                with self._stats_lock:
                    self._active += 1
                try:
                    job.future.set_result(job.fn())
                except Exception as exc:
                    job.future.set_exception(exc)
                finally:
                    with self._stats_lock:
                        self._active -= 1
                        self._completed += 1
            finally:
                self._queue.task_done()

    def run(self, fn: Callable[[], T], *, timeout: float | None = None) -> T:
        wait_timeout = self._default_timeout if timeout is None else timeout
        future: Future[T] = Future()
        job = _Job(fn=fn, future=future)

        try:
            self._queue.put(job, block=False)
        except Full as exc:
            raise QueueFullError(
                "Request queue is full. Please try again shortly."
            ) from exc

        try:
            return future.result(timeout=wait_timeout)
        except TimeoutError as exc:
            raise QueueTimeoutError(
                "Request timed out waiting in queue."
            ) from exc

    def stats(self) -> dict[str, int | float]:
        with self._stats_lock:
            active = self._active
            completed = self._completed

        return {
            "pending": self._queue.qsize(),
            "active": active,
            "completed": completed,
            "workers": self._workers,
            "max_size": self._max_size,
            "min_interval_sec": self._min_interval,
        }


_queue: RequestQueue | None = None


def get_request_queue() -> RequestQueue:
    global _queue
    if _queue is None:
        _queue = RequestQueue(
            workers=int(os.environ.get("QUEUE_WORKERS", "1")),
            max_size=int(os.environ.get("QUEUE_MAX_SIZE", "100")),
            min_interval=float(os.environ.get("QUEUE_MIN_INTERVAL_SEC", "0.5")),
            default_timeout=float(os.environ.get("QUEUE_TIMEOUT_SEC", "120")),
        )
        _queue.start()
    return _queue
