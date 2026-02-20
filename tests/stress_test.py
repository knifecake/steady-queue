#!/usr/bin/env python
"""
Stress test for steady_queue.

Enqueues a configurable number of tasks across multiple queues and runs them
through the full supervisor (multiple workers, multiple threads). After all
tasks complete (or a timeout expires), it checks invariants:

  1. Every enqueued job has finished_at set (no lost jobs).
  2. No jobs are stuck in ready/claimed/blocked state.
  3. No failed executions were recorded (unless expected).
  4. Each job was executed exactly once (no duplicates).

This is the kind of test that surfaces race conditions like:
  - Issue #25: IntegrityError from duplicate ClaimedExecution
  - Issue #26: AttributeError from process being None on execution

Usage (run from project root):
    # Run with defaults (1000 tasks, 3 workers, 4 threads each)
    uv run python tests/stress_test.py

    # Custom parameters
    uv run python tests/stress_test.py --tasks 10000 --workers 3 --threads 4

    # With multiple queues
    uv run python tests/stress_test.py --tasks 5000 --queues default urgent background

    # Shorter timeout for CI
    uv run python tests/stress_test.py --tasks 500 --timeout 60
"""

import argparse
import logging
import os
import subprocess
import sys
import textwrap
import time

# Ensure the project root is on sys.path so "tests.settings" is importable
# when running this script directly (python tests/stress_test.py).
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Django setup - must happen before any Django imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

import django  # noqa: E402

django.setup()

from django.db import connections  # noqa: E402

import steady_queue  # noqa: E402
from steady_queue.models.blocked_execution import BlockedExecution  # noqa: E402
from steady_queue.models.claimed_execution import ClaimedExecution  # noqa: E402
from steady_queue.models.failed_execution import FailedExecution  # noqa: E402
from steady_queue.models.job import Job  # noqa: E402
from steady_queue.models.ready_execution import ReadyExecution  # noqa: E402
from tests.dummy.tasks import stress_counter_task  # noqa: E402

logger = logging.getLogger("stress_test")

COUNTER_TABLE = "stress_test_counter"


# ---------------------------------------------------------------------------
# Counter table helpers (for duplicate-execution detection)
# ---------------------------------------------------------------------------


def ensure_counter_table(db_alias="default"):
    """Create a simple counter table if it doesn't exist."""
    with connections[db_alias].cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {COUNTER_TABLE} (
                job_id BIGINT PRIMARY KEY,
                exec_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )


def reset_counter_table(db_alias="default"):
    with connections[db_alias].cursor() as cursor:
        cursor.execute(f"DELETE FROM {COUNTER_TABLE}")


def get_duplicate_executions(db_alias="default"):
    """Return job_ids that were executed more than once."""
    with connections[db_alias].cursor() as cursor:
        cursor.execute(
            f"SELECT job_id, exec_count FROM {COUNTER_TABLE} WHERE exec_count > 1"
        )
        return cursor.fetchall()


def get_execution_count(db_alias="default"):
    """Return total number of recorded executions."""
    with connections[db_alias].cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {COUNTER_TABLE}")
        return cursor.fetchone()[0]


# ---------------------------------------------------------------------------
# Enqueue phase
# ---------------------------------------------------------------------------


def enqueue_tasks(
    num_tasks: int, queues: list[str], workload: str = "none", batch_size: int = 500
):
    """Enqueue tasks distributed across queues round-robin."""
    logger.info(
        "Enqueueing %d tasks across queues %s (workload=%s) ...",
        num_tasks,
        queues,
        workload,
    )

    start = time.monotonic()
    for i in range(num_tasks):
        queue = queues[i % len(queues)]
        stress_counter_task.using(queue_name=queue).enqueue(job_id=i, workload=workload)

        if (i + 1) % batch_size == 0:
            elapsed = time.monotonic() - start
            rate = (i + 1) / elapsed
            logger.info("  enqueued %d / %d (%.0f tasks/s)", i + 1, num_tasks, rate)

    elapsed = time.monotonic() - start
    logger.info(
        "Enqueued %d tasks in %.1fs (%.0f tasks/s)",
        num_tasks,
        elapsed,
        num_tasks / elapsed,
    )


# ---------------------------------------------------------------------------
# Supervisor launcher (as a subprocess)
# ---------------------------------------------------------------------------


def build_supervisor_script(queues, threads, workers, polling_interval):
    """Return a Python script string that starts the supervisor."""
    return textwrap.dedent(f"""\
        import os, sys
        sys.path.insert(0, {PROJECT_ROOT!r})
        os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"

        import django
        django.setup()

        # Register extra queues with the task backend
        from django.conf import settings
        settings.TASKS["default"]["QUEUES"] = {queues!r}
        from tests.dummy.tasks import stress_counter_task
        backend = stress_counter_task.get_backend()
        backend.queues = set({queues!r})

        from datetime import timedelta
        from steady_queue.configuration import Configuration
        from steady_queue.processes.supervisor import Supervisor

        config = Configuration.Options(
            workers=[
                Configuration.Worker(
                    queues={queues!r},
                    threads={threads!r},
                    processes={workers!r},
                    polling_interval=timedelta(seconds={polling_interval!r}),
                )
            ],
            dispatchers=[
                Configuration.Dispatcher(
                    polling_interval=timedelta(seconds=1),
                    batch_size=500,
                )
            ],
            recurring_tasks=[],
            skip_recurring=True,
        )

        Supervisor.launch(config)
    """)


def start_supervisor(queues, threads, workers, polling_interval):
    """Start the supervisor as a subprocess, return the Popen object."""
    script = build_supervisor_script(queues, threads, workers, polling_interval)
    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
    )
    return proc


# ---------------------------------------------------------------------------
# Wait for completion
# ---------------------------------------------------------------------------


def wait_for_completion(num_tasks: int, timeout: int, poll_interval: float = 2.0):
    """Poll the Job table until all jobs are finished or timeout is hit."""
    db = steady_queue.database

    logger.info("Waiting for %d jobs to complete (timeout=%ds) ...", num_tasks, timeout)
    start = time.monotonic()

    while True:
        elapsed = time.monotonic() - start

        finished = Job.objects.using(db).filter(finished_at__isnull=False).count()
        ready = ReadyExecution.objects.using(db).count()
        claimed = ClaimedExecution.objects.using(db).count()
        failed = FailedExecution.objects.using(db).count()

        logger.info(
            "  [%.0fs] finished=%d ready=%d claimed=%d failed=%d",
            elapsed,
            finished,
            ready,
            claimed,
            failed,
        )

        if finished + failed >= num_tasks:
            logger.info("All jobs accounted for after %.1fs", elapsed)
            return True

        if elapsed > timeout:
            logger.error(
                "Timeout after %ds. Only %d/%d finished.", timeout, finished, num_tasks
            )
            return False

        time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_results(num_tasks: int) -> list[str]:
    """Check invariants and return a list of failure messages (empty = pass)."""
    db = steady_queue.database
    failures = []

    # 1. All jobs should have finished_at set
    total_jobs = Job.objects.using(db).count()
    finished_jobs = Job.objects.using(db).filter(finished_at__isnull=False).count()
    if finished_jobs != num_tasks:
        # Show breakdown by class_name to diagnose unexpected jobs
        from django.db.models import Count

        breakdown = (
            Job.objects.using(db)
            .values("class_name")
            .annotate(n=Count("id"))
            .order_by("-n")
        )
        detail = ", ".join(f"{r['class_name']}: {r['n']}" for r in breakdown)
        failures.append(
            f"FAIL: Expected {num_tasks} finished jobs, got {finished_jobs} "
            f"(total jobs in DB: {total_jobs}). Breakdown: {detail}"
        )

    # 2. No executions should be stuck
    ready = ReadyExecution.objects.using(db).count()
    if ready > 0:
        failures.append(f"FAIL: {ready} ready executions still pending")

    claimed = ClaimedExecution.objects.using(db).count()
    if claimed > 0:
        failures.append(f"FAIL: {claimed} claimed executions still in progress")

    blocked = BlockedExecution.objects.using(db).count()
    if blocked > 0:
        failures.append(f"FAIL: {blocked} blocked executions remain")

    # 3. No unexpected failures
    failed = FailedExecution.objects.using(db).count()
    if failed > 0:
        sample = FailedExecution.objects.using(db).select_related("job").all()[:5]
        reasons = [f"  job {f.job_id}: {f.error}" for f in sample]
        failures.append(f"FAIL: {failed} failed executions:\n" + "\n".join(reasons))

    # 4. No duplicate executions (each job ran exactly once)
    duplicates = get_duplicate_executions()
    if duplicates:
        failures.append(
            f"FAIL: {len(duplicates)} jobs executed more than once: {duplicates[:10]}"
        )

    exec_count = get_execution_count()
    if exec_count != num_tasks:
        failures.append(
            f"FAIL: Expected {num_tasks} execution records, got {exec_count}"
        )

    return failures


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def cleanup_tables():
    """Remove all steady_queue data and the counter table."""
    db = steady_queue.database

    # Order matters due to FK constraints
    ClaimedExecution.objects.using(db).all().delete()
    ReadyExecution.objects.using(db).all().delete()
    FailedExecution.objects.using(db).all().delete()
    BlockedExecution.objects.using(db).all().delete()
    Job.objects.using(db).all().delete()

    reset_counter_table()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args():
    parser = argparse.ArgumentParser(description="Stress test for steady_queue")
    parser.add_argument(
        "--tasks",
        type=int,
        default=1000,
        help="Number of tasks to enqueue (default: 1000)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Number of worker processes (default: 3)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Threads per worker (default: 4)",
    )
    parser.add_argument(
        "--queues",
        nargs="+",
        default=["default", "urgent", "background"],
        help="Queue names (default: default urgent background)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Max seconds to wait for completion (default: 300)",
    )
    parser.add_argument(
        "--polling-interval",
        type=float,
        default=0.1,
        help="Worker polling interval in seconds (default: 0.1)",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip cleanup of DB tables before and after the test",
    )
    parser.add_argument(
        "--workload",
        choices=["none", "light", "medium", "heavy"],
        default="none",
        help="Simulated work per task: none (counter only), light (~10-30ms), "
        "medium (~30-100ms), heavy (~100-300ms) (default: none)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Logging setup
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)-20s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("steady_queue").setLevel(level)
    logging.getLogger("django.tasks").setLevel(logging.WARNING)

    logger.info("=" * 60)
    logger.info("steady_queue stress test")
    logger.info("=" * 60)
    logger.info(
        "Config: tasks=%d workers=%d threads=%d queues=%s workload=%s timeout=%ds",
        args.tasks,
        args.workers,
        args.threads,
        args.queues,
        args.workload,
        args.timeout,
    )

    # Register all requested queues with the Django task backend
    backend = stress_counter_task.get_backend()
    backend.queues = backend.queues | set(args.queues)

    # Setup
    ensure_counter_table()
    if not args.no_cleanup:
        logger.info("Cleaning up previous data ...")
        cleanup_tables()

    # Run migrations (in case test DB is fresh)
    from django.core.management import call_command

    call_command("migrate", "--run-syncdb", verbosity=0)

    # Phase 1: Enqueue all tasks before starting workers
    enqueue_tasks(args.tasks, args.queues, args.workload)

    # Phase 2: Start supervisor as a separate process
    logger.info("Starting supervisor ...")
    supervisor = start_supervisor(
        args.queues, args.threads, args.workers, args.polling_interval
    )
    logger.info("Supervisor started (pid=%d)", supervisor.pid)

    # Phase 3: Wait for completion
    try:
        wait_for_completion(args.tasks, args.timeout)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
    finally:
        # Stop the supervisor
        logger.info("Stopping supervisor (pid=%d) ...", supervisor.pid)
        supervisor.terminate()
        try:
            supervisor.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning("Supervisor didn't stop, killing ...")
            supervisor.kill()
            supervisor.wait()
        logger.info("Supervisor stopped.")

    # Phase 4: Verify
    logger.info("=" * 60)
    logger.info("Verifying results ...")
    logger.info("=" * 60)

    failures = verify_results(args.tasks)

    if failures:
        for f in failures:
            logger.error(f)
        logger.error("STRESS TEST FAILED (%d issues)", len(failures))
        if not args.no_cleanup:
            cleanup_tables()
        sys.exit(1)
    else:
        logger.info("All checks passed.")
        logger.info("STRESS TEST PASSED")

    # Cleanup
    if not args.no_cleanup:
        logger.info("Cleaning up ...")
        cleanup_tables()

    sys.exit(0)


if __name__ == "__main__":
    main()
