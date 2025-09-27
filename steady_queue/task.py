import datetime
import uuid
from typing import Any, Optional

from django.utils import timezone, translation
from django.utils.module_loading import import_string
from django_tasks import Task
from django_tasks.task import P, T, TaskResult

from steady_queue.arguments import Arguments


class UnknownTaskClassError(Exception):
    pass


class SteadyQueueTask(Task[P, T]):
    args: P.args
    kwargs: P.kwargs

    concurrency_key: Optional[str] = None
    concurrency_limit: Optional[int] = None
    concurrency_duration: Optional[timezone.timedelta] = None
    concurrency_group: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.arguments = {}

    @property
    def id(self) -> str:
        return str(uuid.uuid4())

    def using(
        self,
        *,
        priority: Optional[int] = None,
        queue_name: Optional[str] = None,
        run_after: Optional[datetime.datetime | datetime.timedelta] = None,
        backend: Optional[str] = None,
    ):
        if isinstance(run_after, datetime.timedelta):
            run_after = timezone.now() + run_after

        return super().using(
            priority=priority,
            queue_name=queue_name,
            run_after=run_after,
            backend=backend,
        )

    def enqueue(self, *args: P.args, **kwargs: P.kwargs) -> "TaskResult[T]":
        return self.get_backend().enqueue(self, args, kwargs)

    def set_arguments(self, arguments: dict[str, Any]):
        self.arguments = arguments

    def serialize(self):
        return {
            "class_name": self.module_path,
            "job_id": self.id,  # TODO: make it stable
            "backend": self.backend,
            "queue_name": self.queue_name,
            "priority": self.priority,
            "arguments": Arguments.serialize_args_and_kwargs(self.args, self.kwargs),
            "locale": translation.get_language(),
            "timezone": timezone.get_current_timezone_name(),
            "enqueued_at": timezone.now().isoformat(),
            "scheduled_at": self.run_after.isoformat() if self.run_after else None,
        }

    @classmethod
    def execute(cls, job_data: dict[str, Any]):
        task = cls.deserialize(job_data)
        task.func(*task.args, **task.kwargs)

    @classmethod
    def deserialize(cls, job_data: dict[str, Any]):
        try:
            task_class = import_string(job_data["class_name"])
        except ImportError as e:
            raise UnknownTaskClassError(job_data["class_name"]) from e

        task = task_class.using(
            priority=job_data["priority"],
            queue_name=job_data["queue_name"],
            run_after=job_data["scheduled_at"],
            backend=job_data["backend"],
        )

        task.args, task.kwargs = Arguments.deserialize_args_and_kwargs(
            job_data["arguments"]
        )
        return task
