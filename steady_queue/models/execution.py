from typing import Self

from django.db import models, transaction

from .base import BaseModel


class ExecutionQuerySet(models.QuerySet):
    def in_order(self) -> Self:
        return self.order_by("priority", "job_id")

    def discard_in_batches(self, batch_size: int = 500) -> int:
        pending = self.count()
        total_discarded = 0

        while True:
            with transaction.atomic():
                to_discard = self.order_by("job_id").select_for_update()[:batch_size]
                discarded = self.discard_jobs(to_discard)
                pending -= discarded
                total_discarded += discarded

            if pending == 0:
                break

            if discarded == 0:
                break

        return total_discarded

    def discard_all_from_jobs(self, jobs: models.QuerySet):
        raise NotImplementedError

    def discard_jobs(self, executions: models.QuerySet) -> int:
        from steady_queue.models.job import Job

        _, discarded_by_type = Job.objects.filter(
            id__in=executions.values_list("job_id", flat=True)
        ).delete()

        return discarded_by_type.get("steady_queue.Job", 0)


class Execution(BaseModel):
    class Meta:
        abstract = True

    @property
    def type(self):
        raise NotImplementedError
