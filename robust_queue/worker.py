import logging
from datetime import timedelta

from django.db import models
from django.utils import timezone

from robust_queue.configuration import Configuration
from robust_queue.models.ready_execution import ReadyExecution
from robust_queue.pool import Pool
from robust_queue.processes.poller import Poller

logger = logging.getLogger("robust_queue")


class Worker(Poller):
    pool: Pool

    def __init__(self, options: Configuration.WorkerConfiguration):
        self.queues = options.queues
        self.pool = Pool(options.threads, on_idle=lambda: self.wake_up())

        super().__init__(polling_interval=options.polling_interval)

    def poll(self) -> timedelta:
        claimed_executions = self.claim_executions()
        for execution in claimed_executions:
            logger.info("%s claimed job %s", self.name, execution.job_id)
            self.pool.post(execution)

        return self.polling_interval if self.pool.is_idle else timedelta(minutes=10)

    def claim_executions(self) -> models.QuerySet:
        return ReadyExecution.objects.claim(
            self.queues, self.pool.idle_threads, self.process_id
        )

    def shutdown(self):
        self.pool.shutdown()
        # TODO: self.pool.wait_for_termination(timeout=timedelta(seconds=10))

        super().shutdown()

    def is_all_work_completed(self) -> bool:
        return ReadyExecution.objects.aggregated_count_across_queues(self.queues) == 0
