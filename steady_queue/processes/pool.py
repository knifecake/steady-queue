import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Callable

from steady_queue.app_executor import AppExecutor
from steady_queue.models.claimed_execution import ClaimedExecution
from steady_queue.processes.concurrent import AtomicInteger

logger = logging.getLogger("steady_queue")


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
                with AppExecutor.wrap_in_app_executor():
                    execution.perform()
                    logger.info(
                        "%(worker)s completed job %(job_id)s %(class_name)s",
                        {
                            "worker": execution.process.name,
                            "job_id": execution.job_id,
                            "class_name": execution.job.class_name,
                        },
                    )
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
