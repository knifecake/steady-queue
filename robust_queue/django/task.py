import uuid
from typing import Any

from django.utils import timezone, translation
from django.utils.module_loading import import_string
from django_tasks import Task

from robust_queue.job.errors import UnknownJobClassError


class RobustQueueTask(Task):
    arguments = dict[str, Any]

    def __post_init__(self):
        self.arguments = {}

    @property
    def id(self) -> str:
        return str(uuid.uuid4())

    def set_arguments(self, arguments: dict[str, Any]):
        self.arguments = arguments

    def serialize(self):
        return {
            "class_name": self.module_path,  # TODO: support classes
            "job_id": self.id,  # TODO: make it stable
            "backend": self.backend,
            "queue_name": self.queue_name,
            "priority": self.priority,
            "arguments": self.arguments,
            "locale": translation.get_language(),
            "timezone": timezone.get_current_timezone_name(),
            "enqueued_at": timezone.now().isoformat(),
            "scheduled_at": self.run_after.isoformat() if self.run_after else None,
        }

    @classmethod
    def execute(cls, job_data: dict[str, Any]):
        task = cls.deserialize(job_data)
        task.func(**task.arguments)

    @classmethod
    def deserialize(cls, job_data: dict[str, Any]):
        try:
            task_class = import_string(job_data["class_name"])
        except ImportError as e:
            raise UnknownJobClassError(job_data["class_name"]) from e

        task = task_class.using(
            priority=job_data["priority"],
            queue_name=job_data["queue_name"],
            run_after=job_data["scheduled_at"],
            backend=job_data["backend"],
        )

        task.set_arguments(job_data["arguments"])
        return task
