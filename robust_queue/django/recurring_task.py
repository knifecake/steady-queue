import logging
from typing import Any

from robust_queue.configuration import Configuration
from robust_queue.django.task import RobustQueueTask

logger = logging.getLogger("robust_queue")
configurations = []


def recurring_task(
    schedule: str,
    key: str,
    arguments: dict[str, Any] = None,
    queue_name: str = None,
    priority: int = 0,
    description: str = None,
):
    """
    Decorator for registering a task to run on a recurring schedule.

    Usage:
        @recurring_task(schedule="*/1 * * * *", key="unique_task_key")
        @task()
        def my_recurring_task():
            print("This runs every minute")
    """

    def wrapper(task: RobustQueueTask):
        class_name = task.module_path
        configuration = Configuration.RecurringTaskConfiguration(
            key=key,
            class_name=class_name,
            schedule=schedule,
            arguments=arguments,
            queue_name=queue_name,
            priority=priority,
            description=description,
        )
        configurations.append(configuration)
        logger.info("Configured recurring task: %s", configuration)

        return task

    return wrapper
