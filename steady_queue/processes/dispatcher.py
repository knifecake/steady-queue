import logging
from datetime import timedelta
from typing import Any, Optional

from steady_queue.app_executor import AppExecutor
from steady_queue.configuration import Configuration
from steady_queue.models.blocked_execution import BlockedExecution
from steady_queue.models.scheduled_execution import ScheduledExecution
from steady_queue.models.semaphore import Semaphore
from steady_queue.processes.poller import Poller
from steady_queue.processes.timer import TimerTask

logger = logging.getLogger("steady_queue")


class Dispatcher(Poller):
    batch_size: int
    concurrency_maintenance: Optional["ConcurrencyMaintenance"] = None

    def __init__(self, options: Configuration.Dispatcher):
        self.batch_size = options.batch_size
        if options.concurrency_maintenance:
            self.concurrency_maintenance = self.ConcurrencyMaintenance(
                interval=options.concurrency_maintenance_interval,
                batch_size=options.batch_size,
            )

        super().__init__(polling_interval=options.polling_interval)

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            **super().metadata,
            "batch_size": self.batch_size,
            "concurrency_maintenance_interval": self.concurrency_maintenance.interval
            if self.concurrency_maintenance
            else None,
        }

    def boot(self):
        super().boot()
        self.start_concurrency_maintenance()

    def shutdown(self):
        self.stop_concurrency_maintenance()
        super().shutdown()

    def poll(self) -> timedelta:
        batch = self.dispatch_next_batch()
        if batch > 0:
            logger.debug("%s dispatched %d jobs", self.name, batch)
        return self.polling_interval if batch == 0 else timedelta(seconds=0)

    def dispatch_next_batch(self) -> int:
        return ScheduledExecution.dispatch_next_batch(self.batch_size)

    def start_concurrency_maintenance(self):
        if self.concurrency_maintenance:
            self.concurrency_maintenance.start()

    def stop_concurrency_maintenance(self):
        if self.concurrency_maintenance:
            self.concurrency_maintenance.stop()

    @property
    def is_all_work_completed(self) -> bool:
        return ScheduledExecution.objects.count() == 0

    class ConcurrencyMaintenance:
        def __init__(self, interval: timedelta, batch_size: int):
            self.interval = interval
            self.batch_size = batch_size

        def start(self):
            self.concurrency_maintenance_task = TimerTask(
                interval=self.interval, callable=self.run, run_now=True
            )
            self.concurrency_maintenance_task.start()

        def stop(self):
            self.concurrency_maintenance_task.stop()

        def run(self):
            self.expire_semaphores()
            self.unblock_blocked_executions()

        def expire_semaphores(self):
            with AppExecutor.wrap_in_app_executor():
                semaphores = Semaphore.objects.expired().iterator(
                    chunk_size=self.batch_size
                )
                for semaphore in semaphores:
                    semaphore.delete()

        def unblock_blocked_executions(self):
            with AppExecutor.wrap_in_app_executor():
                BlockedExecution.objects.unblock(self.batch_size)
