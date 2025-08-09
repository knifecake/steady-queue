import logging
from datetime import datetime
from threading import Timer

from robust_queue.configuration import Configuration
from robust_queue.models.recurring_task import RecurringTask
from robust_queue.processes.concurrent import Dict

logger = logging.getLogger("robust_queue")


class RecurringSchedule:
    def __init__(
        self, tasks: list[RecurringTask | Configuration.RecurringTaskConfiguration]
    ):
        self.configured_tasks: list[RecurringTask] = [
            RecurringTask.wrap(t) for t in tasks
        ]
        self.scheduled_tasks = Dict()

    def is_empty(self) -> bool:
        return len(self.configured_tasks) == 0

    def schedule_tasks(self):
        self.persist_tasks()
        self.reload_tasks()

        for t in self.configured_tasks:
            self.schedule_task(t)

    def schedule_task(self, task):
        self.scheduled_tasks[task.key] = self.schedule(task)

    def unschedule_tasks(self):
        for t in self.scheduled_tasks.values():
            t.cancel()

        self.scheduled_tasks.clear()

    @property
    def task_keys(self) -> list[str]:
        return list(map(lambda t: t.key, self.configured_tasks))

    def persist_tasks(self):
        RecurringTask.objects.static().exclude(key__in=self.task_keys).delete()
        RecurringTask.objects.create_or_update_all(self.configured_tasks)

    def reload_tasks(self):
        self.configured_tasks = RecurringTask.objects.filter(key__in=self.task_keys)

    def schedule(self, task: RecurringTask):
        def timer_callback(
            recurring_schedule: "RecurringSchedule",
            task: RecurringTask,
            run_at: datetime,
        ):
            # schedule the next execution
            logger.debug("scheduling next execution for %s", task.key)
            recurring_schedule.schedule_task(task)

            # enqueue the current one
            task.enqueue(run_at=run_at)
            logger.debug("enqueued current execution for %s", task.key)

        scheduled_task = Timer(
            interval=task.delay_from_now.total_seconds(),
            function=timer_callback,
            args=(self, task, task.next_time),
        )
        scheduled_task.start()
        return scheduled_task
