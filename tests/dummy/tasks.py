import time

from django.tasks import task

from steady_queue.concurrency import limits_concurrency
from steady_queue.recurring_task import recurring


@task()
def dummy_task():
    print("dummy task")


@task()
def failing_task():
    raise Exception("this is a task that always fails")


@task()
def task_with_args(name):
    print(f"hello {name}, from task_with_args")


@task()
def update_all_names(name):
    from tests.dummy.models import Dummy

    print(f"Updating name to {name} in all Dummy models")

    for dummy in Dummy.objects.all():
        dummy.name = name
        dummy.save()


@task()
def long_running_task():
    print("long running task")
    time.sleep(10)
    print("long running task finished")


@limits_concurrency(key="limited_task")
@task()
def limited_task(duration: int = 10):
    print(f"limited task for {duration} seconds")
    time.sleep(duration)
    print("limited task finished")


@recurring(schedule="*/1 * * * *", key="dummy_recurring_task")
@task()
def dummy_recurring_task():
    print("dummy recurring task")


@recurring(schedule="*/1 * * * *", key="dummy_recurring_task_2")
@task()
def dummy_recurring_task_2():
    print("dummy recurring task 2")
