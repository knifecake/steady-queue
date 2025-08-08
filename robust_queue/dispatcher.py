import logging
from datetime import timedelta
from typing import Any

from robust_queue.configuration import Configuration
from robust_queue.models.scheduled_execution import ScheduledExecution
from robust_queue.processes.poller import Poller

logger = logging.getLogger("robust_queue")


class Dispatcher(Poller):
    batch_size: int

    def __init__(self, options: Configuration.DispatcherConfiguration):
        self.batch_size = options.batch_size
        super().__init__(polling_interval=options.polling_interval)

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            **super().metadata,
            "batch_size": self.batch_size,
        }

    def poll(self) -> timedelta:
        batch = self.dispatch_next_batch()
        if batch > 0:
            logger.debug("%s dispatched %d jobs", self.name, batch)
        return self.polling_interval if batch == 0 else timedelta(seconds=0)

    def dispatch_next_batch(self) -> int:
        return ScheduledExecution.dispatch_next_batch(self.batch_size)

    @property
    def is_all_work_completed(self) -> bool:
        return ScheduledExecution.objects.count() == 0
