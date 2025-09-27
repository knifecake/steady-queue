from django.db import models
from django.utils import timezone

from steady_queue.models.base import BaseModel, UpdatedAtMixin


class SemaphoreQuerySet(models.QuerySet):
    def wait(self, job) -> bool:
        return Semaphore.Proxy(job).wait()

    def signal(self, job) -> bool:
        return Semaphore.Proxy(job).signal()

    def signal_all(self, jobs) -> int:
        return Semaphore.Proxy.signal_all(jobs)

    def available(self):
        return self.filter(value__gt=0)

    def expired(self):
        return self.filter(expires_at__lte=timezone.now())


class Semaphore(UpdatedAtMixin, BaseModel):
    class Meta:
        verbose_name = "semaphore"
        verbose_name_plural = "semaphores"
        constraints = (
            models.UniqueConstraint(fields=("key",), name="uq_sq_semaphore_key"),
        )
        indexes = (
            models.Index(fields=("expires_at",), name="ix_sq_semaphore_expires_at"),
            models.Index(fields=("key", "value"), name="ix_sq_semaphores_key_value"),
        )

    objects = SemaphoreQuerySet.as_manager()

    key = models.CharField(max_length=255, verbose_name="key")
    value = models.IntegerField(default=1, verbose_name="value")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="expires at")

    class Proxy:
        def __init__(self, job):
            self.job = job

        def wait(self) -> bool:
            try:
                semaphore = Semaphore.objects.get(key=self.key)
                return semaphore.value > 0 and self.attempt_decrement()
            except Semaphore.DoesNotExist:
                return self.attempt_creation()

        def signal(self) -> bool:
            return self.attempt_increment()

        @classmethod
        def signal_all(cls, jobs) -> int:
            return Semaphore.objects.filter(
                key=[job.concurrency_key for job in jobs]
            ).update(value=models.F("value") + 1)

        def attempt_creation(self) -> bool:
            semaphore, created = Semaphore.objects.get_or_create(
                key=self.key,
                defaults={"value": self.limit - 1, "expires_at": self.expires_at},
            )
            if created:
                return True

            return self.check_limit_or_decrement()

        def check_limit_or_decrement(self) -> bool:
            if self.limit == 1:
                return False
            return self.attempt_decrement()

        def attempt_decrement(self) -> bool:
            updated = (
                Semaphore.objects.available()
                .filter(key=self.key)
                .update(value=models.F("value") - 1, expires_at=self.expires_at)
            )
            return updated > 0

        def attempt_increment(self) -> bool:
            updated = Semaphore.objects.filter(
                key=self.key, value__lte=self.limit
            ).update(value=models.F("value") + 1, expires_at=self.expires_at)
            return updated > 0

        @property
        def key(self) -> str:
            return self.job.concurrency_key

        @property
        def expires_at(self) -> timezone.datetime:
            return timezone.now() + self.job.concurrency_duration

        @property
        def limit(self) -> int:
            return self.job.concurrency_limit or 1
