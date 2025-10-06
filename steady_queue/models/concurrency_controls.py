from django.db import models
from django.utils.module_loading import import_string

from steady_queue.models.blocked_execution import BlockedExecution

from .semaphore import Semaphore


class ConcurrencyControlsQuerySet(models.QuerySet):
    def release_all_concurrency_locks(self, jobs):
        Semaphore.signal_all(filter(lambda job: job.is_concurrency_limited, jobs))


class ConcurrencyControls:
    @property
    def concurrency_limit(self):
        return self.job_class.concurrency_limit

    @property
    def concurrency_duration(self):
        return self.job_class.concurrency_duration

    def unblock_next_blocked_job(self):
        if self.release_concurrency_lock():
            self.release_next_blocked_job()

    @property
    def is_concurrency_limited(self) -> bool:
        return self.concurrency_key is not None

    @property
    def is_blocked(self) -> bool:
        return self.blocked_execution is not None

    def acquire_concurrency_lock(self) -> bool:
        if not self.is_concurrency_limited:
            return True

        return Semaphore.objects.wait(self)

    def release_concurrency_lock(self) -> bool:
        if not self.is_concurrency_limited:
            return False

        return Semaphore.objects.signal(self)

    def block(self):
        BlockedExecution.objects.get_or_create(job=self)

    def release_next_blocked_job(self):
        BlockedExecution.objects.release_one(self.concurrency_key)

    @property
    def job_class(self):
        return import_string(self.class_name)

    @property
    def execution(self):
        return super().execution or self.blocked_execution

    def delete(self, *args, **kwargs):
        if self.is_concurrency_limited and self.is_ready:
            self.unblock_next_blocked_job()

        return super().delete(*args, **kwargs)
