import logging
from datetime import timedelta
from typing import Optional

from robust_queue.configuration import Configuration
from robust_queue.models.recurring_task import RecurringTask
from robust_queue.processes.base import Base
from robust_queue.processes.interruptible import Interruptible
from robust_queue.processes.registrable import Registrable
from robust_queue.processes.runnable import Runnable
from robust_queue.recurring_schedule import RecurringSchedule

logger = logging.getLogger("robust_queue")


class Scheduler(Runnable, Interruptible, Registrable, Base):
    SLEEP_INTERVAL = timedelta(minutes=1)

    def __init__(
        self,
        recurring_tasks: Optional[
            list[RecurringTask | Configuration.RecurringTaskConfiguration]
        ] = None,
        **kwargs,
    ):
        if recurring_tasks is None:
            recurring_tasks = []

        self.recurring_schedule = RecurringSchedule(recurring_tasks)
        super().__init__(**kwargs)

    @property
    def metadata(self):
        return {
            **super().metadata,
            "recurring_schedule": self.recurring_schedule.task_keys,
        }

    def boot(self):
        super().boot()
        self.schedule_recurring_tasks()

    def run(self):
        try:
            while True:
                if self.is_shutting_down:
                    break

                self.interruptible_sleep(self.SLEEP_INTERVAL)
        finally:
            self.shutdown()

    def shutdown(self):
        self.unschedule_recurring_tasks()
        super().shutdown()

    def schedule_recurring_tasks(self):
        logger.info(
            "Scheduling recurring tasks from %s", self.recurring_schedule.task_keys
        )
        self.recurring_schedule.schedule_tasks()

    def unschedule_recurring_tasks(self):
        self.recurring_schedule.unschedule_tasks()

    @property
    def is_all_work_completed(self):
        return self.recurring_schedule is None  # TODO
