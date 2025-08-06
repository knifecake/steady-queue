from django_tasks import ResultStatus, TaskResult
from django_tasks.backends.base import BaseTaskBackend
from django_tasks.exceptions import ResultDoesNotExist

from robust_queue.django.task import RobustQueueTask
from robust_queue.models import Job


class RobustQueueBackend(BaseTaskBackend):
    task_class = RobustQueueTask

    def enqueue(self, task: RobustQueueTask, args, kwargs) -> TaskResult:
        if args:
            raise ValueError("robust queue does not support positional arguments yet")

        task.set_arguments(kwargs)
        job = Job.enqueue(task, scheduled_at=task.run_after)
        return self.to_task_result(task, job)

    def get_result(self, result_id: str) -> TaskResult:
        raise ResultDoesNotExist

    def to_task_result(self, task: RobustQueueTask, job: Job):
        return TaskResult(
            task=task,
            id=job.id,
            status=ResultStatus.READY,
            enqueued_at=job.created_at,
            started_at=None,
            finished_at=job.finished_at,
            last_attempted_at=None,
            args=None,
            kwargs=task.arguments,
            backend=task.backend,
            errors=[],
            worker_ids=[],
        )
