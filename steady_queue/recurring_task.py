import logging
from dataclasses import replace
from typing import Optional

from steady_queue.configuration import Configuration
from steady_queue.task import SteadyQueueTask

logger = logging.getLogger("steady_queue")
configurations = []


def recurring(
    schedule: str,
    key: str,
    args: Optional[list] = None,
    kwargs: Optional[dict] = None,
    queue_name: Optional[str] = None,
    priority: int = 0,
    description: Optional[str] = None,
):
    """
    Decorator for registering a task to run on a recurring schedule.

    Usage:

        @recurring(schedule="*/1 * * * *", key="unique_task_key")
        @task()
        def my_recurring_task():
            print("This runs every minute")
    """

    def wrapper(task: SteadyQueueTask):
        try:
            class_name = task.module_path
        except AttributeError:
            raise ValueError(
                "The given task does not look to be a Django task. Did you forget to decorate it with @task()?"
            )

        configuration = Configuration.RecurringTask(
            key=key,
            class_name=class_name,
            schedule=schedule,
            arguments=task.serialize(),
            queue_name=queue_name,
            priority=priority,
            description=description,
        )
        configurations.append(configuration)

        return replace(task, args=args, kwargs=kwargs)

    return wrapper
