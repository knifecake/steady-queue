import logging
from datetime import timedelta

from django.db import models

from steady_queue.configuration import Configuration
from steady_queue.models.ready_execution import ReadyExecution
from steady_queue.processes.poller import Poller
from steady_queue.processes.pool import Pool

logger = logging.getLogger("steady_queue")


class Worker(Poller):
    pool: Pool

    def __init__(self, options: Configuration.WorkerConfiguration):
        self.queues = options.queues
        self.pool = Pool(options.threads, on_idle=lambda: self.wake_up())

        super().__init__(polling_interval=options.polling_interval)

    @property
    def metadata(self):
        return {
            **super().metadata,
            "queues": ",".join(self.queues),
            "thread_pool_size": self.pool.size,
        }

    def poll(self) -> timedelta:
        claimed_executions = self.claim_executions()
        for execution in claimed_executions:
            logger.info(
                "%(worker)s claimed job %(job_id)s %(class_name)s",
                {
                    "worker": self.name,
                    "job_id": execution.job_id,
                    "class_name": execution.job.class_name,
                },
            )
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

    @property
    def is_all_work_completed(self) -> bool:
        return ReadyExecution.objects.aggregated_count_across_queues(self.queues) == 0
