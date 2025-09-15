from django_tasks import task

from steady_queue import recurring


@task()
def dummy_task():
    print("dummy task")


@recurring(schedule="*/1 * * * *", key="dummy_recurring_task")
@task()
def dummy_recurring_task():
    print("dummy recurring task")


@recurring(schedule="*/1 * * * *", key="dummy_recurring_task_2")
@task()
def dummy_recurring_task_2():
    print("dummy recurring task 2")
