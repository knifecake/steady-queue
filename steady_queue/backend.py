from typing import Any

from django.tasks import Task, TaskResult, TaskResultStatus
from django.tasks.backends.base import BaseTaskBackend
from django.tasks.signals import task_enqueued

from steady_queue.arguments import Arguments
from steady_queue.task import SteadyQueueTask


class SteadyQueueBackend(BaseTaskBackend):
    task_class = SteadyQueueTask

    supports_defer = True

    supports_async_task = False

    supports_get_result = False

    def validate_task(self, task: Task) -> None:
        # TODO: do we need to do anything here?
        super().validate_task(task)

    def enqueue(
        self, task: SteadyQueueTask, args: list, kwargs: dict[str, Any]
    ) -> TaskResult:
        from steady_queue.models import Job

        if not isinstance(task, SteadyQueueTask):
            raise ValueError("Steady Queue only supports SteadyQueueTasks")

        job = Job.objects.enqueue(task, args, kwargs)
        task_result = self.to_task_result(task, job, args, kwargs)
        task_enqueued.send(sender=self, task_result=task_result)
        return task_result

    def execute(self, task, job):
        job_data = job.arguments
        args, kwargs = Arguments.deserialize_args_and_kwargs(job_data["arguments"])
        task.func(*args, **kwargs)

    def get_result(self, result_id: str) -> TaskResult:
        raise NotImplementedError(
            "This backend does not support retrieving or refreshing results."
        )

    def to_task_result(
        self, task: SteadyQueueTask, job, args: list, kwargs: dict[str, Any]
    ) -> TaskResult:
        if job.status == "finished":
            status = TaskResultStatus.SUCCESSFUL
        elif job.status == "failed":
            status = TaskResultStatus.FAILED
        elif job.status == "claimed":
            status = TaskResultStatus.RUNNING
        else:
            status = TaskResultStatus.READY

        return TaskResult(
            task=task,
            id=str(job.id),
            status=status,
            enqueued_at=job.created_at,
            started_at=None,
            finished_at=job.finished_at,
            last_attempted_at=None,
            args=args,
            kwargs=kwargs,
            backend=task.backend,
            errors=[],
            worker_ids=[],
        )
