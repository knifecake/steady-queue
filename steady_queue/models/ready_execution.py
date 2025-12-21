from django.db import models, transaction

from steady_queue.models.claimed_execution import ClaimedExecution
from steady_queue.queue_selector import QueueSelector

from .execution import Execution, ExecutionQuerySet


class ReadyExecutionQuerySet(ExecutionQuerySet, models.QuerySet):
    def queued_as(self, queue_name: str) -> models.QuerySet:
        return self.filter(queue_name=queue_name)

    def create_all_from_jobs(self, jobs):
        jobs = [
            self.model(job=job, **self.model.attributes_from_job(job)) for job in jobs
        ]
        return self.bulk_create(jobs)  # TODO: conflicts?

    def claim(self, queue_list, limit, process_id) -> list[ClaimedExecution]:
        scoped_relations = QueueSelector(
            queue_list, self.model.objects
        ).scoped_relations()

        claimed: list[ClaimedExecution] = []
        for relation in scoped_relations:
            locked = relation.select_and_lock(process_id, limit)
            limit -= len(locked)
            claimed.extend(locked)

        return claimed

    def select_and_lock(self, process_id, limit) -> models.QuerySet:
        if limit <= 0:
            return self.none()

        with transaction.atomic(using=self.db):
            candidates = self.select_candidates(limit)
            claimed = candidates.lock_candidates(process_id)
            return claimed

    def select_candidates(self, limit):
        return (
            self.in_order()
            .select_for_update(skip_locked=True)
            .only("id", "job_id")[:limit]
        )

    def lock_candidates(self, process_id):
        from steady_queue.models.claimed_execution import ClaimedExecution

        claimed_executions = list(
            ClaimedExecution.objects.claiming(
                self.values_list("job_id", flat=True), process_id
            )
        )

        for claimed in claimed_executions:
            self.model.objects.filter(job_id=claimed.job_id).delete()

        return claimed_executions

    def aggregated_count_across_queues(self, queues: list[str]) -> int:
        # TODO: queue selection
        return self.count()


class ReadyExecution(Execution):
    class Meta:
        verbose_name = "ready execution"
        verbose_name_plural = "ready executions"
        indexes = (
            models.Index(fields=("priority", "job"), name="ix_sq_poll_all"),
            models.Index(
                fields=("queue_name", "priority", "created_at"),
                name="ix_sq_poll_for_queue",
            ),
        )

    objects = ReadyExecutionQuerySet.as_manager()

    job = models.OneToOneField(
        "Job",
        verbose_name="job",
        on_delete=models.CASCADE,
        related_name="ready_execution",
    )

    queue_name = models.CharField(max_length=255, verbose_name="queue name")
    priority = models.IntegerField(default=0, verbose_name="priority")

    @property
    def type(self):
        return "ready"

    @classmethod
    def attributes_from_job(cls, job):
        return {
            "queue_name": job.queue_name,
            "priority": job.priority,
        }

    def __str__(self) -> str:
        return f"{self.job_id} {self.queue_name}"
