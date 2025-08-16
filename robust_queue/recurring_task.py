import logging
from typing import Optional

from robust_queue.configuration import Configuration
from robust_queue.task import RobustQueueTask

logger = logging.getLogger("robust_queue")
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

        @recurring_task(schedule="*/1 * * * *", key="unique_task_key")
        @task()
        def my_recurring_task():
            print("This runs every minute")
    """

    def wrapper(task: RobustQueueTask):
        class_name = task.module_path
        task.args = args
        task.kwargs = kwargs
        configuration = Configuration.RecurringTaskConfiguration(
            key=key,
            class_name=class_name,
            schedule=schedule,
            arguments=task.serialize(),
            queue_name=queue_name,
            priority=priority,
            description=description,
        )
        configurations.append(configuration)
        logger.info("Configured recurring task: %s", configuration)

        return task

    return wrapper
