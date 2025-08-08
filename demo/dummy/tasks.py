import time

from django_tasks import task

from robust_queue.django.recurring_task import recurring_task


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


@recurring_task(schedule="*/1 * * * *", key="rt1 once per minute")
@task()
def recurring_task1():
    """
    This is a recurring task that runs every minute.
    """
    print("I am a recurring task")
