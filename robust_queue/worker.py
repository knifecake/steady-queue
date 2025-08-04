import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.utils import timezone

from robust_queue.processes.poller import Poller

logger = logging.getLogger("robust_queue")


class Worker(Poller):
    def __init__(self, **kwargs):
        defaults = {
            "polling_interval": timezone.timedelta(seconds=1),
            "queues": ["*"],
            "max_workers": 1,
        }
        defaults.update(kwargs)

        self.queues = defaults.pop("queues")
        self.pool = ThreadPoolExecutor(max_workers=defaults.pop("max_workers"))

        super().__init__(**defaults)

    def poll(self) -> timedelta:
        # TODO: implement
        logger.info("worker poll")
        return self.polling_interval
