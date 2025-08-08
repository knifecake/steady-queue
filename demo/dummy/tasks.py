import time

from django_tasks import task


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
    return 1 / 0
