import logging

import steady_queue
from steady_queue.models.claimed_execution import ClaimedExecution
from steady_queue.models.process import Process
from steady_queue.processes.errors import ProcessMissingError
from steady_queue.processes.timer import TimerTask

logger = logging.getLogger("steady_queue")


class Maintenance:
    def launch_maintenance_task(self):
        logger.debug("launching maintenance task")
        self.maintenance_task = TimerTask(
            interval=steady_queue.process_alive_threshold,
            callable=lambda: self.prune_dead_processes(),
        )

        self.maintenance_task.start()

    def stop_maintenance_task(self):
        self.maintenance_task.stop()

    def fail_orphaned_executions(self):
        ClaimedExecution.objects.orphaned().fail_all_with(ProcessMissingError())

    def prune_dead_processes(self):
        logger.debug("pruning dead processes")
        Process.objects.exclude(pk=self.process.pk).prune()
