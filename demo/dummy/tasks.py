import time

from django_tasks import task
from steady_queue.recurring_task import recurring


@task()
def task1():
    print("AAAAAAA")


@task()
def long_running_task(duration: int):
    for i in range(duration, 0, -1):
        print(f"Long running task: {i} remaining...")
        time.sleep(1)


@task()
def exception_task():
    """
    This task always raises an exception.
    """
    return 1 / 0


@recurring(schedule="*/1 * * * *", key="rt1 once per minute")
@task()
def recurring_task1():
    """
    This is a recurring task that runs every minute.
    """
    print("I am a recurring task")


@task()
def task_with_args(a: int, b: int):
    print(f"a + b = {a + b}")


@task()
def task_with_kwargs(name: str = "John"):
    print(f"Hello, {name}!")
