from django.utils import timezone

from robust_queue.processes.errors import ProcessPrunedError


class PrunableQuerySetMixin:
    def prune(self, excluding=None):
        prunable = self.prunable()

        if excluding is not None:
            prunable = prunable.exclude(id__in=map(excluding, lambda p: p.id))

        prunable.select_for_update(skip_locked=True).iterator(batch_size=50)

        for process in prunable:
            process.prune()

    def prunable(self):
        return self.filter(
            last_heartbeat_at__lt=timezone.now() - timezone.timedelta(seconds=10)
        )


class PrunableMixin:
    def prune(self):
        error = ProcessPrunedError(self.last_heartbeat_at)
        self.fail_all_claimed_executions_with(error)

        self.deregister(pruned=True)
