from dataclasses import replace
from datetime import timedelta
from typing import Optional

import steady_queue
from steady_queue.task import SteadyQueueTask


def limits_concurrency(
    key: str,
    to: int = 1,
    duration: Optional[timedelta] = None,
    group: Optional[str] = None,
):
    def wrapper(task: SteadyQueueTask):
        return replace(
            task,
            concurrency_key=key,
            concurrency_limit=to,
            concurrency_duration=duration
            or steady_queue.default_concurrency_control_period,
            concurrency_group=group or task.module_path,
        )

    return wrapper
