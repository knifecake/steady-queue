from django.db import models
from django.utils import timezone

from steady_queue.models.scheduled_execution import ScheduledExecution


class SchedulableQuerySet(models.QuerySet):
    def scheduled(self):
        # NOTE: this implementation deviates from solid queue's implementation.
        # Instead of checking for not finished jobs, we check for jobs that have
        # a scheduled execution.
        return self.filter(scheduled_execution__isnull=False)

    def successfully_scheduled(self, jobs):
        return self.filter(scheduled_execution__job__in=jobs)


class Schedulable:
    @classmethod
    def schedule_all(cls, jobs):
        cls.schedule_all_at_once(jobs)
        return cls.objects.successfully_scheduled(jobs)

    @classmethod
    def schedule_all_at_once(cls, jobs):
        ScheduledExecution.objects.create_all_from_jobs(jobs)

    @property
    def is_due(self):
        return self.scheduled_at is None or self.scheduled_at <= timezone.now()

    @property
    def is_scheduled(self):
        return self.scheduled_execution is not None

    def schedule(self):
        return ScheduledExecution.objects.get_or_create(
            job=self,
            defaults=ScheduledExecution.attributes_from_job(self),
        )

    @property
    def execution(self):
        return super().execution or self.scheduled_execution
