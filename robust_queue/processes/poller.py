import logging
from datetime import timedelta
from typing import Any

from robust_queue.processes.base import Base
from robust_queue.processes.interruptible import Interruptible
from robust_queue.processes.registrable import Registrable
from robust_queue.processes.runnable import Runnable

logger = logging.getLogger("robust_queue")


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
        self.start_loop()

    def start_loop(self):
        try:
            while True:
                logger.debug("poller started loop")
                if self.is_shutting_down:
                    logger.info("poller shutting down")
                    break

                delay = self.poll()
                self.interruptible_sleep(delay)
        finally:
            self.shutdown()

    def poll(self) -> timedelta:
        raise NotImplementedError
