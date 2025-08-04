from django.db import models
from django.utils import timezone

from robust_queue.models.ready_execution import ReadyExecution
from robust_queue.models.retryable import Retryable, RetryableQuerySet
from robust_queue.models.schedulable import Schedulable, SchedulableQuerySet


class ExecutableQuerySet(RetryableQuerySet, SchedulableQuerySet, models.QuerySet):
    def finished(self):
        return self.filter(finished_at__isnull=False)

    def successfully_dispatched(self, jobs):
        return self.dispatched_and_ready(jobs).union(self.dispatched_and_blocked(jobs))

    def dispatched_and_ready(self, jobs):
        return self.filter(ready_execution__job__in=jobs)

    def dispatched_and_blocked(self, jobs):
        return self.filter(scheduled_execution__job__in=jobs)


class Executable(Schedulable, Retryable):
    @classmethod
    def prepare_all_for_execution(cls, jobs):
        due = [j for j in jobs if j.is_due]
        not_yet_due = [j for j in jobs if not j.is_due]

        return cls.dispatch_all(due) + cls.schedule_all(not_yet_due)

    @classmethod
    def dispatch_all(cls, jobs):
        # TODO: concurrency limits
        without_concurrency_limits = [j for j in jobs if not j.concurrency_key]
        with_concurrency_limits = [j for j in jobs if j.concurrency_key]

        cls.dispatch_all_at_once(without_concurrency_limits)
        cls.dispatch_all_one_by_one(with_concurrency_limits)

        return cls.objects.successfully_dispatched(jobs)

    @classmethod
    def dispatch_all_at_once(cls, jobs):
        ReadyExecution.objects.create_all_from_jobs(jobs)

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
        # TODO: concurrency limits
        return self.ready

    def dispatch_bypassing_concurrency_limits(self):
        return self.ready

    def finished(self):
        # TODO: preserve_finished_jobs?
        self.finished_at = timezone.now()
        self.save(update_fields=("finished_at",))

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
        ReadyExecution.get_or_create(job=self)

    @property
    def execution(self):
        return self.ready_execution or self.claimed_execution or self.failed_execution
