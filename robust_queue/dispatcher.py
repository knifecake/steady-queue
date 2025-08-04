from datetime import timedelta
from typing import Any

from django.utils import timezone

from robust_queue.models.scheduled_execution import ScheduledExecution
from robust_queue.processes.poller import Poller


class Dispatcher(Poller):
    batch_size: int

    def __init__(self, **kwargs):
        defaults = {
            "polling_interval": timezone.timedelta(seconds=1),
            "batch_size": 100,
        }
        defaults.update(kwargs)

        self.batch_size = defaults.pop("batch_size")

        super().__init__(**defaults)

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            **super().metadata,
            "batch_size": self.batch_size,
        }

    def poll(self) -> timedelta:
        return self.polling_interval

        batch = self.dispatch_next_batch()
        if batch == 0:
            return self.polling_interval
        else:
            return timedelta(seconds=0)

    def dispatch_next_batch(self) -> int:
        return ScheduledExecution.dispatch_next_batch(self.batch_size)

    @property
    def is_all_work_completed(self) -> bool:
        return ScheduledExecution.objects.count() == 0
