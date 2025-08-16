import steady_queue
from django.utils import timezone
from steady_queue.processes.errors import ProcessPrunedError


class PrunableQuerySet:
    def prunable(self):
        return self.filter(
            last_heartbeat_at__lt=timezone.now() - steady_queue.process_alive_threshold
        )

    def prune(self):
        prunable = self.prunable()

        prunable.select_for_update(skip_locked=True).iterator(chunk_size=50)

        for process in prunable:
            process.prune()


class Prunable:
    def prune(self):
        error = ProcessPrunedError(self.last_heartbeat_at)
        self.fail_all_claimed_executions_with(error)

        self.deregister(pruned=True)
