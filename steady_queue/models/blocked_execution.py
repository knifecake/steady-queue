from django.db import models, transaction
from django.utils import timezone

from steady_queue.models.execution import Execution, ExecutionQuerySet
from steady_queue.models.ready_execution import ReadyExecution
from steady_queue.models.semaphore import Semaphore


class BlockedExecutionQuerySet(ExecutionQuerySet):
    def expired(self):
        return self.filter(expires_at__lte=timezone.now())

    def unblock(self, limit: int):
        concurrency_keys = (
            self.expired()
            .order_by("concurrency_key")
            .distinct()
            .values_list("concurrency_key", flat=True)[:limit]
        )
        return self.release_many(concurrency_keys)

    def release_many(self, concurrency_keys: list[str]) -> int:
        return sum(1 for key in concurrency_keys if self.release_one(key))

    def release_one(self, concurrency_key: str):
        with transaction.atomic(using=self.db):
            execution = (
                self.in_order()
                .filter(concurrency_key=concurrency_key)
                .select_for_update(skip_locked=True)
                .first()
            )
            if execution:
                return execution.release()

    def releasable(self, concurrency_keys: list[str]) -> list[str]:
        semaphores = dict(
            Semaphore.objects.filter(key__in=concurrency_keys).values("key", "value")
        )

        # Concurrency keys without semaphore + concurrency keys with open semaphore
        return [
            key
            for key in concurrency_keys
            if key not in semaphores or semaphores[key] > 0
        ]


class BlockedExecution(Execution):
    class Meta:
        verbose_name = "blocked task"
        verbose_name_plural = "blocked tasks"
        indexes = (
            models.Index(
                fields=("concurrency_key", "priority", "job"),
                name="ix_sq_blocked_for_release",
            ),
            models.Index(
                fields=("expires_at", "concurrency_key"),
                name="ix_sq_blocked_for_maintenance",
            ),
        )

    objects = BlockedExecutionQuerySet.as_manager()

    job = models.OneToOneField(
        "Job",
        verbose_name="job",
        on_delete=models.CASCADE,
        related_name="blocked_execution",
    )
    queue_name = models.CharField(max_length=255, verbose_name="queue name")
    priority = models.IntegerField(default=0, verbose_name="priority")
    concurrency_key = models.CharField(max_length=255, verbose_name="concurrency key")
    expires_at = models.DateTimeField(verbose_name="expires at")

    @property
    def semaphore(self):
        try:
            return Semaphore.objects.get(key=self.concurrency_key)
        except Semaphore.DoesNotExist:
            return None

    @property
    def type(self):
        return "blocked"

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.concurrency_key = self.job.concurrency_key
            self.set_expires_at()

        return super().save(*args, **kwargs)

    def set_expires_at(self):
        self.expires_at = timezone.now() + self.job.concurrency_duration

    def release(self) -> bool:
        with transaction.atomic(using=self._state.db):
            if self.acquire_concurrency_lock():
                self.promote_to_ready()
                self.delete()
                return True

        return False

    def acquire_concurrency_lock(self) -> bool:
        return Semaphore.objects.wait(self.job)

    def promote_to_ready(self):
        ReadyExecution.objects.create(
            job=self.job, queue_name=self.queue_name, priority=self.priority
        )
