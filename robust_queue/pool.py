import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Callable

from robust_queue.models.claimed_execution import ClaimedExecution

logger = logging.getLogger("robust_queue")


class AtomicInteger:
    def __init__(self, value: int):
        self._value = value
        self._lock = Lock()

    @property
    def value(self):
        with self._lock:
            return self._value

    def increment(self):
        with self._lock:
            self._value += 1
            return self._value

    def decrement(self):
        with self._lock:
            self._value -= 1
            return self._value


class Pool:
    size: int

    def __init__(self, size: int, on_idle: Callable):
        self.size = size
        self.on_idle = on_idle
        self.available_threads = AtomicInteger(size)
        self.mutex = Lock()
        self.executor = ThreadPoolExecutor(max_workers=size)

    def post(self, execution: ClaimedExecution):
        self.available_threads.decrement()

        def wrapped_execution():
            try:
                execution.perform()
            finally:
                self.available_threads.increment()
                with self.mutex:
                    if self.is_idle and self.on_idle:
                        self.on_idle()

        self.executor.submit(wrapped_execution)
        logger.debug("posted execution %s", execution.pk)

    @property
    def idle_threads(self):
        return self.available_threads.value

    @property
    def is_idle(self):
        return self.available_threads.value > 0

    def shutdown(self):
        self.executor.shutdown(wait=False, cancel_futures=True)
