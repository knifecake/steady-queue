from django.db import models
from django.utils import timezone

import steady_queue
from steady_queue.models.concurrency_controls import (
    ConcurrencyControls,
    ConcurrencyControlsQuerySet,
)
from steady_queue.models.ready_execution import ReadyExecution
from steady_queue.models.retryable import Retryable, RetryableQuerySet
from steady_queue.models.schedulable import Schedulable, SchedulableQuerySet


class ExecutableQuerySet(
    ConcurrencyControlsQuerySet, RetryableQuerySet, SchedulableQuerySet, models.QuerySet
):
    def ready(self):
        return self.filter(ready_execution__isnull=False)

    def claimed(self):
        return self.filter(claimed_execution__isnull=False)

    def blocked(self):
        return self.filter(blocked_execution__isnull=False)

    def finished(self):
        return self.filter(finished_at__isnull=False)

    def successfully_dispatched(self, jobs):
        return self.dispatched_and_ready(jobs).union(self.dispatched_and_blocked(jobs))

    def dispatched_and_ready(self, jobs):
        return self.filter(ready_execution__job__in=jobs)

    def dispatched_and_blocked(self, jobs):
        return self.filter(scheduled_execution__job__in=jobs)


class Executable(ConcurrencyControls, Schedulable, Retryable):
    @classmethod
    def prepare_all_for_execution(cls, jobs):
        due = [j for j in jobs if j.is_due]
        not_yet_due = [j for j in jobs if not j.is_due]

        return cls.dispatch_all(due) + cls.schedule_all(not_yet_due)

    @classmethod
    def dispatch_all(cls, jobs):
        without_concurrency_limits = [j for j in jobs if not j.is_concurrency_limited]
        with_concurrency_limits = [j for j in jobs if j.is_concurrency_limited]

        cls.dispatch_all_at_once(without_concurrency_limits)
        cls.dispatch_all_one_by_one(with_concurrency_limits)

        return cls.objects.successfully_dispatched(jobs)

    @classmethod
    def dispatch_all_at_once(cls, jobs):
        return ReadyExecution.objects.create_all_from_jobs(jobs)

    @classmethod
    def dispatch_all_one_by_one(cls, jobs):
        for job in jobs:
            job.dispatch()

    @property
    def is_ready(self):
        return self.ready_execution is not None

    @property
    def is_claimed(self):
        return self.claimed_execution is not None

    @property
    def is_failed(self):
        return self.failed_execution is not None

    def prepare_for_execution(self):
        if self.is_due:
            return self.dispatch()
        else:
            return self.schedule()

    def dispatch(self):
        if self.acquire_concurrency_lock():
            return self.ready
        else:
            return self.block()

    def dispatch_bypassing_concurrency_limits(self):
        return self.ready

    def finished(self):
        if steady_queue.preserve_finished_jobs:
            self.finished_at = timezone.now()
            self.save(update_fields=("finished_at",))
        else:
            self.delete()

    @property
    def is_finished(self):
        return self.finished_at is not None

    @property
    def status(self):
        if self.is_finished:
            return "finished"

        return self.execution.type

    @property
    def ready(self):
        return ReadyExecution.objects.get_or_create(
            job=self,
            defaults=ReadyExecution.attributes_from_job(self),
        )

    @property
    def execution(self):
        return (
            getattr(self, "ready_execution", None)
            or getattr(self, "claimed_execution", None)
            or getattr(self, "failed_execution", None)
            or getattr(self, "scheduled_execution", None)
            or getattr(self, "blocked_execution", None)
        )

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)

        if creating:
            self.prepare_for_execution()
