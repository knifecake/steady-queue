from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

import steady_queue
from steady_queue.models import (
    BlockedExecution,
    ClaimedExecution,
    FailedExecution,
    Job,
    Process,
    ReadyExecution,
    ScheduledExecution,
    Semaphore,
)
from tests.dummy.tasks import dummy_task, limited_task, limited_task_with_lambda_key


class TestHelperMixin:
    """Helper methods for creating test data."""

    @classmethod
    def create_test_process(cls, name="test-worker-1"):
        """Create a Process record for testing claims."""
        return Process.objects.create(
            name=name,
            kind="Worker",
            pid=12345,
            hostname="test-host",
            last_heartbeat_at=timezone.now(),
        )

    @classmethod
    def create_job_in_queue(cls, queue_name, priority=0):
        """Create a job directly in a specific queue."""
        job = Job.objects.create(
            queue_name=queue_name,
            priority=priority,
            class_name="tests.dummy.tasks.dummy_task",
            arguments={"arguments": {"args": [], "kwargs": {}}},
            scheduled_at=timezone.now(),
        )
        return job


class ReadyExecutionTestCase(TestHelperMixin, TestCase):
    """Tests for ReadyExecution claiming and ordering."""

    def test_queued_as_filters_by_queue(self):
        """queued_as returns only jobs in that queue."""
        self.create_job_in_queue("queue1")
        self.create_job_in_queue("queue1")
        self.create_job_in_queue("queue2")

        self.assertEqual(ReadyExecution.objects.queued_as("queue1").count(), 2)
        self.assertEqual(ReadyExecution.objects.queued_as("queue2").count(), 1)

    def test_in_order_respects_priority_then_job_id(self):
        """Jobs should be ordered by priority (descending) then job_id."""
        job_low = self.create_job_in_queue("default", priority=1)
        job_high = self.create_job_in_queue("default", priority=10)

        ordered = list(ReadyExecution.objects.in_order())
        self.assertEqual(ordered[0].job_id, job_high.id)
        self.assertEqual(ordered[1].job_id, job_low.id)

    def test_claim_returns_claimed_executions(self):
        """claim() should return claimed executions and move them from ready."""
        process = self.create_test_process()
        for _ in range(5):
            Job.objects.enqueue(dummy_task, [], {})

        self.assertEqual(ReadyExecution.objects.count(), 5)

        claimed = ReadyExecution.objects.claim(
            queue_list=["*"], limit=3, process_id=process.id
        )

        self.assertEqual(len(claimed), 3)
        self.assertEqual(ReadyExecution.objects.count(), 2)
        self.assertEqual(ClaimedExecution.objects.count(), 3)

    def test_claim_respects_limit(self):
        """claim() should not exceed the limit."""
        process = self.create_test_process()
        for _ in range(10):
            Job.objects.enqueue(dummy_task, [], {})

        claimed = ReadyExecution.objects.claim(
            queue_list=["*"], limit=3, process_id=process.id
        )

        self.assertEqual(len(claimed), 3)

    def test_claim_with_zero_limit_returns_empty(self):
        """claim() with limit=0 should return nothing."""
        process = self.create_test_process()
        Job.objects.enqueue(dummy_task, [], {})

        claimed = ReadyExecution.objects.claim(
            queue_list=["*"], limit=0, process_id=process.id
        )

        self.assertEqual(len(claimed), 0)
        self.assertEqual(ReadyExecution.objects.count(), 1)


class ClaimedExecutionTestCase(TestHelperMixin, TestCase):
    """Tests for ClaimedExecution behavior."""

    def test_claimed_execution_tracks_process(self):
        """Claimed execution should track which process claimed it."""
        process = self.create_test_process()
        Job.objects.enqueue(dummy_task, [], {})

        claimed = ReadyExecution.objects.claim(
            queue_list=["*"], limit=1, process_id=process.id
        )

        self.assertEqual(claimed[0].process_id, process.id)

    def test_orphaned_returns_executions_without_process(self):
        """orphaned() should find executions with null process_id."""
        process = self.create_test_process()
        Job.objects.enqueue(dummy_task, [], {})
        claimed = ReadyExecution.objects.claim(
            queue_list=["*"], limit=1, process_id=process.id
        )

        # Simulate orphan by clearing process
        claimed[0].process_id = None
        claimed[0].save()

        self.assertEqual(ClaimedExecution.objects.orphaned().count(), 1)

    def test_fail_all_with_creates_failed_executions(self):
        """fail_all_with() should fail all claimed executions."""
        process = self.create_test_process()
        for _ in range(3):
            Job.objects.enqueue(dummy_task, [], {})

        ReadyExecution.objects.claim(queue_list=["*"], limit=3, process_id=process.id)

        ClaimedExecution.objects.fail_all_with("worker crashed")

        self.assertEqual(ClaimedExecution.objects.count(), 0)
        self.assertEqual(FailedExecution.objects.count(), 3)


class ScheduledExecutionTestCase(TestHelperMixin, TestCase):
    """Tests for ScheduledExecution dispatching."""

    def create_scheduled_job(self, scheduled_at, priority=0):
        """Create a job that stays in scheduled state."""
        job = Job.objects.create(
            queue_name="default",
            priority=priority,
            class_name="tests.dummy.tasks.dummy_task",
            arguments={"arguments": {"args": [], "kwargs": {}}},
            scheduled_at=scheduled_at,
        )
        # The job was created as ready/scheduled based on scheduled_at
        # For past jobs, we need to manually create scheduled execution
        if scheduled_at <= timezone.now():
            # Job went to ready, we need to test scheduled path differently
            pass
        return job

    def test_due_returns_past_scheduled_jobs(self):
        """due() should return jobs scheduled in the past."""
        # Create jobs with future schedule first, then update to test due()
        past_time = timezone.now() - timedelta(hours=1)
        future_time = timezone.now() + timedelta(hours=1)

        # Create future job (will be scheduled)
        job_future = Job.objects.create(
            queue_name="default",
            class_name="tests.dummy.tasks.dummy_task",
            arguments={"arguments": {"args": [], "kwargs": {}}},
            scheduled_at=future_time,
        )

        self.assertEqual(ScheduledExecution.objects.count(), 1)

        # Update to past to test due() filter
        ScheduledExecution.objects.filter(job=job_future).update(scheduled_at=past_time)

        self.assertEqual(ScheduledExecution.objects.due().count(), 1)

    def test_next_batch_respects_limit(self):
        """next_batch() should respect the batch_size limit."""
        past_time = timezone.now() - timedelta(hours=1)
        future_time = timezone.now() + timedelta(hours=1)

        # Create 10 future jobs
        for _ in range(10):
            Job.objects.create(
                queue_name="default",
                class_name="tests.dummy.tasks.dummy_task",
                arguments={"arguments": {"args": [], "kwargs": {}}},
                scheduled_at=future_time,
            )

        # Update all to past
        ScheduledExecution.objects.update(scheduled_at=past_time)

        batch = ScheduledExecution.objects.next_batch(3)
        self.assertEqual(batch.count(), 3)

    def test_dispatch_next_batch_moves_to_ready(self):
        """dispatch_next_batch() should move scheduled jobs to ready."""
        future_time = timezone.now() + timedelta(hours=1)
        past_time = timezone.now() - timedelta(hours=1)

        # Create 5 future jobs
        for _ in range(5):
            Job.objects.create(
                queue_name="default",
                class_name="tests.dummy.tasks.dummy_task",
                arguments={"arguments": {"args": [], "kwargs": {}}},
                scheduled_at=future_time,
            )

        self.assertEqual(ScheduledExecution.objects.count(), 5)
        self.assertEqual(ReadyExecution.objects.count(), 0)

        # Update to past so they're due
        ScheduledExecution.objects.update(scheduled_at=past_time)

        dispatched = ScheduledExecution.dispatch_next_batch(batch_size=3)

        self.assertEqual(dispatched, 3)
        self.assertEqual(ScheduledExecution.objects.count(), 2)
        self.assertEqual(ReadyExecution.objects.count(), 3)

    def test_dispatch_next_batch_returns_zero_when_empty(self):
        """dispatch_next_batch() should return 0 when nothing to dispatch."""
        dispatched = ScheduledExecution.dispatch_next_batch(batch_size=10)
        self.assertEqual(dispatched, 0)

    def test_in_order_respects_scheduled_time_then_priority(self):
        """Jobs should be ordered by scheduled_at, then priority (descending)."""
        earlier = timezone.now() + timedelta(hours=1)
        later = timezone.now() + timedelta(hours=2)

        # Create jobs with different scheduled times
        # Within same scheduled time, higher priority (larger number) comes first
        job_later_low = Job.objects.create(
            queue_name="default",
            priority=1,
            class_name="tests.dummy.tasks.dummy_task",
            arguments={"arguments": {"args": [], "kwargs": {}}},
            scheduled_at=later,
        )
        job_earlier_high = Job.objects.create(
            queue_name="default",
            priority=10,
            class_name="tests.dummy.tasks.dummy_task",
            arguments={"arguments": {"args": [], "kwargs": {}}},
            scheduled_at=earlier,
        )

        # Earlier scheduled time takes precedence over priority
        ordered = list(ScheduledExecution.objects.in_order())
        self.assertEqual(ordered[0].job_id, job_earlier_high.id)
        self.assertEqual(ordered[1].job_id, job_later_low.id)


class BlockedExecutionTestCase(TestCase):
    """Tests for BlockedExecution release mechanics."""

    def test_blocked_execution_stores_concurrency_key(self):
        """Blocked execution should store the concurrency key."""
        # Exhaust semaphore
        Job.objects.enqueue(limited_task, [], {})
        job = Job.objects.enqueue(limited_task, [], {})
        job.refresh_from_db()

        self.assertEqual(job.blocked_execution.concurrency_key, "limited_task")

    def test_release_one_promotes_to_ready(self):
        """release_one() should move one blocked execution to ready."""
        # Create blocked jobs
        Job.objects.enqueue(limited_task, [], {})  # Ready
        Job.objects.enqueue(limited_task, [], {})  # Blocked
        Job.objects.enqueue(limited_task, [], {})  # Blocked

        self.assertEqual(BlockedExecution.objects.count(), 2)
        self.assertEqual(ReadyExecution.objects.count(), 1)

        # Release semaphore to allow unblocking
        Semaphore.objects.filter(key="limited_task").update(value=1)

        released = BlockedExecution.objects.release_one("limited_task")

        self.assertTrue(released)
        self.assertEqual(BlockedExecution.objects.count(), 1)
        self.assertEqual(ReadyExecution.objects.count(), 2)

    def test_release_one_returns_false_when_semaphore_exhausted(self):
        """release_one() should return False when semaphore is still exhausted."""
        # Create blocked jobs
        Job.objects.enqueue(limited_task, [], {})
        Job.objects.enqueue(limited_task, [], {})

        # Semaphore is still at 0
        released = BlockedExecution.objects.release_one("limited_task")

        self.assertFalse(released)
        self.assertEqual(BlockedExecution.objects.count(), 1)

    def test_expired_returns_executions_past_expiry(self):
        """expired() should return executions past their expiry time."""
        # Create blocked job
        Job.objects.enqueue(limited_task, [], {})
        job = Job.objects.enqueue(limited_task, [], {})
        job.refresh_from_db()

        # Manually expire it
        BlockedExecution.objects.filter(job=job).update(
            expires_at=timezone.now() - timedelta(hours=1)
        )

        self.assertEqual(BlockedExecution.objects.expired().count(), 1)


class LambdaConcurrencyKeyTestCase(TestCase):
    """Tests for lambda-based concurrency keys."""

    def test_lambda_concurrency_key_is_computed_from_args(self):
        """Lambda concurrency key should be computed from task arguments."""
        job = Job.objects.enqueue(
            limited_task_with_lambda_key, [42], {"message": "test"}
        )
        job.refresh_from_db()

        self.assertEqual(job.concurrency_key, "account_42")

    def test_lambda_concurrency_key_blocks_same_key(self):
        """Tasks with the same computed key should block each other."""
        job1 = Job.objects.enqueue(limited_task_with_lambda_key, [100], {})
        job2 = Job.objects.enqueue(limited_task_with_lambda_key, [100], {})

        job1.refresh_from_db()
        job2.refresh_from_db()

        # First job should be ready
        self.assertEqual(ReadyExecution.objects.filter(job=job1).count(), 1)
        # Second job with same key should be blocked
        self.assertEqual(BlockedExecution.objects.filter(job=job2).count(), 1)
        self.assertEqual(job2.blocked_execution.concurrency_key, "account_100")

    def test_lambda_concurrency_key_allows_different_keys(self):
        """Tasks with different computed keys should not block each other."""
        job1 = Job.objects.enqueue(limited_task_with_lambda_key, [100], {})
        job2 = Job.objects.enqueue(limited_task_with_lambda_key, [200], {})

        job1.refresh_from_db()
        job2.refresh_from_db()

        # Both should be ready since they have different keys
        self.assertEqual(ReadyExecution.objects.filter(job=job1).count(), 1)
        self.assertEqual(ReadyExecution.objects.filter(job=job2).count(), 1)
        self.assertEqual(job1.concurrency_key, "account_100")
        self.assertEqual(job2.concurrency_key, "account_200")


class FailedExecutionTestCase(TestCase):
    """Tests for FailedExecution retry mechanics."""

    def test_retry_moves_back_to_ready(self):
        """retry() should move failed execution back to ready."""
        job = Job.objects.enqueue(dummy_task, [], {})
        job.ready_execution.delete()
        job.failed_with("test error")

        self.assertEqual(FailedExecution.objects.count(), 1)

        job.failed_execution.retry()

        job.refresh_from_db()
        self.assertEqual(FailedExecution.objects.count(), 0)
        self.assertEqual(job.status, "ready")

    def test_retry_queryset_retries_all(self):
        """FailedExecution.objects.retry() should retry all failed jobs."""
        for _ in range(3):
            job = Job.objects.enqueue(dummy_task, [], {})
            job.ready_execution.delete()
            job.failed_with("error")

        self.assertEqual(FailedExecution.objects.count(), 3)

        count = FailedExecution.objects.retry()

        self.assertEqual(count, 3)
        self.assertEqual(FailedExecution.objects.count(), 0)
        self.assertEqual(ReadyExecution.objects.count(), 3)


class ProcessPruningTestCase(TestHelperMixin, TestCase):
    def test_prune_works(self):
        old_heartbeat = (
            timezone.now() - steady_queue.process_alive_threshold - timedelta(minutes=1)
        )

        Process.objects.create(
            name="old-worker-1",
            kind="Worker",
            pid=11111,
            hostname="test-host",
            last_heartbeat_at=old_heartbeat,
        )
        Process.objects.create(
            name="old-worker-2",
            kind="Worker",
            pid=22222,
            hostname="test-host",
            last_heartbeat_at=old_heartbeat,
        )

        recent_process = Process.objects.create(
            name="active-worker",
            kind="Worker",
            pid=33333,
            hostname="test-host",
            last_heartbeat_at=timezone.now(),
        )

        self.assertEqual(Process.objects.count(), 3)
        self.assertEqual(Process.objects.prunable().count(), 2)

        Process.objects.prune()

        self.assertEqual(Process.objects.count(), 1)
        self.assertEqual(Process.objects.first().id, recent_process.id)
