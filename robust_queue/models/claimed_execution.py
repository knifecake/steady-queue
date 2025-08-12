import logging

from django.db import models, transaction

from robust_queue.models.execution import Execution, ExecutionQuerySet
from robust_queue.task import RobustQueueTask

logger = logging.getLogger("robust_queue")


class ClaimedExecutionQuerySet(ExecutionQuerySet, models.QuerySet):
    def orphaned(self):
        return self.filter(process_id=None)

    def claiming(self, job_ids, process_id):
        claimed_executions = [
            self.model(job_id=job_id, process_id=process_id) for job_id in job_ids
        ]
        self.bulk_create(claimed_executions)

        return self.filter(job_id__in=job_ids)

    def release_all(self):
        for execution in self.all():
            execution.release()

    def fail_all_with(self, error: Exception | str):
        executions = self.select_related("job").all()
        for execution in executions:
            execution.failed_with(error)
            execution.unblock_next_job()

    def discard_in_batches(self, batch_size: int = 500):
        raise ValueError("Cannot discard jobs in progress")


class ClaimedExecution(Execution):
    class Meta:
        verbose_name = "in-progress task"
        verbose_name_plural = "in-progress tasks"
        indexes = (
            models.Index(
                fields=("process_id", "job_id"), name="ix_rq_claimed_process_job"
            ),
        )

    objects = ClaimedExecutionQuerySet.as_manager()

    job = models.OneToOneField(
        "Job",
        verbose_name="job",
        on_delete=models.CASCADE,
        related_name="claimed_execution",
    )
    process = models.ForeignKey(
        "Process",
        verbose_name="process",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="claimed_executions",
    )

    @property
    def type(self):
        return "claimed"

    def unblock_next_job(self):
        self.job.unblock_next_blocked_job()

    def perform(self):
        logger.debug("performing claimed execution for job %s", self.job_id)
        try:
            RobustQueueTask.execute(self.job.arguments)
            self.finished()
        except Exception as e:
            logger.exception("claimed execution failed", exc_info=e)
            self.failed_with(e)

    def finished(self):
        logger.debug("claimed execution for job %s finished", self.job_id)
        with transaction.atomic():
            self.job.finished()
            self.delete()

    def failed_with(self, error: Exception | str):
        logger.debug("claimed execution for job %s failed with %s", self.job_id, error)
        with transaction.atomic():
            self.job.failed_with(error)
            self.delete()
