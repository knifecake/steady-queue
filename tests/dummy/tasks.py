import time

from django_tasks import task

from steady_queue.recurring_task import recurring


@task()
def dummy_task():
    print("dummy task")


@task()
def long_running_task():
    print("long running task")
    time.sleep(10)
    print("long running task finished")


@recurring(schedule="*/1 * * * *", key="dummy_recurring_task")
@task()
def dummy_recurring_task():
    print("dummy recurring task")


@recurring(schedule="*/1 * * * *", key="dummy_recurring_task_2")
@task()
def dummy_recurring_task_2():
    print("dummy recurring task 2")
