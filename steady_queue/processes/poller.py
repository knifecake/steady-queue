import logging
from datetime import timedelta
from typing import Any

from steady_queue.app_executor import AppExecutor
from steady_queue.processes.base import Base
from steady_queue.processes.interruptible import Interruptible
from steady_queue.processes.registrable import Registrable
from steady_queue.processes.runnable import Runnable

logger = logging.getLogger("steady_queue")


class Poller(Runnable, Interruptible, Registrable, Base):
    polling_interval: timedelta

    def __init__(self, polling_interval: timedelta, **kwargs):
        self.polling_interval = polling_interval
        super().__init__(**kwargs)

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            **super().metadata,
            "polling_interval": self.polling_interval,
        }

    def run(self):
        logger.info(
            "%(name)s polling every %(polling_interval)g seconds",
            {
                "name": self.name,
                "polling_interval": self.polling_interval.total_seconds(),
            },
        )
        self.start_loop()

    def start_loop(self):
        try:
            while True:
                if self.is_shutting_down:
                    break

                with AppExecutor.wrap_in_app_executor():
                    delay = self.poll()

                self.interruptible_sleep(delay)
        finally:
            self.shutdown()

    def poll(self) -> timedelta:
        raise NotImplementedError
