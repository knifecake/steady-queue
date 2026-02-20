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


@limits_concurrency(key=lambda account_id, **kwargs: f"account_{account_id}")
@task()
def limited_task_with_lambda_key(account_id: int, message: str = "hello"):
    print(f"limited task for account {account_id}: {message}")


@task(queue_name="default")
def stress_counter_task(job_id: int, workload: str = "none"):
    """Increment execution counter for a job_id. Used by the stress test to detect duplicates.

    workload controls how much simulated work each task performs:
      - "none":   just the counter write (fast, tests queue machinery only)
      - "light":  ~10-30ms sleep + ~1k hash rounds + counter write
      - "medium": ~30-100ms sleep + ~5k hash rounds + counter write
      - "heavy":  ~100-300ms sleep + ~20k hash rounds + counter write
    """
    import hashlib
    import random
    import time

    # Workload profiles: (sleep_min_ms, sleep_max_ms, hash_rounds_min, hash_rounds_max)
    profiles = {
        "none": (0, 0, 0, 0),
        "light": (10, 30, 500, 1500),
        "medium": (30, 100, 3000, 8000),
        "heavy": (100, 300, 15000, 25000),
    }
    sleep_min, sleep_max, rounds_min, rounds_max = profiles.get(
        workload, profiles["none"]
    )

    # IO-bound: simulate an external API call / file write
    if sleep_max > 0:
        time.sleep(random.randint(sleep_min, sleep_max) / 1000.0)

    # CPU-bound: iterative hashing
    if rounds_max > 0:
        data = f"stress-task-{job_id}".encode()
        for _ in range(random.randint(rounds_min, rounds_max)):
            data = hashlib.sha256(data).digest()

    # DB write: always runs (this is our duplicate-execution detector)
    from django.db import connections

    conn = connections["default"]
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO stress_test_counter (job_id, exec_count) VALUES (%s, 1)
            ON CONFLICT (job_id) DO UPDATE SET exec_count = stress_test_counter.exec_count + 1
            """,
            [job_id],
        )
