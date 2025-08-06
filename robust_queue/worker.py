import logging
from datetime import timedelta

from django.db import models
from django.utils import timezone

from robust_queue.models.ready_execution import ReadyExecution
from robust_queue.pool import Pool
from robust_queue.processes.poller import Poller

logger = logging.getLogger("robust_queue")


class Worker(Poller):
    pool: Pool

    def __init__(self, **kwargs):
        defaults = {
            "polling_interval": timezone.timedelta(seconds=1),
            "queues": ["*"],
            "max_workers": 1,
        }
        defaults.update(kwargs)

        self.queues = defaults.pop("queues")
        self.pool = Pool(defaults.pop("max_workers"), on_idle=lambda: self.wake_up())

        super().__init__(**defaults)

    def poll(self) -> timedelta:
        claimed_executions = self.claim_executions()
        logger.debug("worker claimed %d jobs", len(claimed_executions))
        for execution in claimed_executions:
            logger.info("claimed job %s", execution.job_id)
            self.pool.post(execution)

        return self.polling_interval if self.pool.is_idle else timedelta(minutes=10)

    def claim_executions(self) -> models.QuerySet:
        return ReadyExecution.objects.claim(self.queues, 2, self.process_id)

    def shutdown(self):
        self.pool.shutdown()
        # TODO: self.pool.wait_for_termination(timeout=timedelta(seconds=10))

        super().shutdown()

    def is_all_work_completed(self) -> bool:
        return ReadyExecution.objects.aggregated_count_across_queues(self.queues) == 0
