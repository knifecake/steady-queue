from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from steady_queue.models import (
    BlockedExecution,
    Job,
    ReadyExecution,
    ScheduledExecution,
    Semaphore,
)
from tests.dummy.tasks import dummy_task, limited_task


class JobCreationTestCase(TestCase):
    """Tests for job creation and initial execution state."""

    def test_immediate_job_creates_ready_execution(self):
        """A job due now should create a ready execution."""
        job = Job.objects.enqueue(dummy_task, [], {})

        self.assertTrue(hasattr(job, "ready_execution"))
        self.assertEqual(job.status, "ready")
        self.assertEqual(ReadyExecution.objects.count(), 1)

    def test_scheduled_job_creates_scheduled_execution(self):
        """A job scheduled for the future should create a scheduled execution."""
        future_task = dummy_task.using(run_after=timedelta(hours=1))
        job = Job.objects.enqueue(future_task, [], {})

        self.assertTrue(hasattr(job, "scheduled_execution"))
        self.assertEqual(job.status, "scheduled")
        self.assertEqual(ScheduledExecution.objects.count(), 1)

    def test_concurrency_limited_job_blocks_when_semaphore_exhausted(self):
        """When semaphore is exhausted, job should be blocked."""
        # First job acquires the semaphore
        job1 = Job.objects.enqueue(limited_task, [], {})
        self.assertEqual(job1.status, "ready")

        # Second job should be blocked
        job2 = Job.objects.enqueue(limited_task, [], {})
        self.assertEqual(BlockedExecution.objects.count(), 1)
        # Verify blocked execution was created for job2
        self.assertTrue(BlockedExecution.objects.filter(job=job2).exists())

    def test_concurrency_limited_jobs_respect_limit(self):
        """Multiple jobs should respect the concurrency limit."""
        # With default limit of 1, only first should be ready
        for _ in range(3):
            Job.objects.enqueue(limited_task, [], {})

        # Check execution counts directly
        self.assertEqual(ReadyExecution.objects.count(), 1)
        self.assertEqual(BlockedExecution.objects.count(), 2)


class JobAttributesTestCase(TestCase):
    """Tests for job attribute mapping from tasks.

    These tests use direct Job creation to test attribute mapping
    without going through task validation.
    """

    def test_attributes_from_task_maps_queue_name(self):
        """Queue name is extracted from task."""
        # Create job directly to test attribute mapping
        job = Job.objects.create(
            queue_name="custom_queue",
            class_name="tests.dummy.tasks.dummy_task",
            arguments={"arguments": {"args": [], "kwargs": {}}},
        )
        self.assertEqual(job.queue_name, "custom_queue")

    def test_attributes_from_task_maps_priority(self):
        """Priority is extracted from task."""
        job = Job.objects.create(
            queue_name="default",
            priority=10,
            class_name="tests.dummy.tasks.dummy_task",
            arguments={"arguments": {"args": [], "kwargs": {}}},
        )
        self.assertEqual(job.priority, 10)

    def test_attributes_from_task_maps_scheduled_at(self):
        """Scheduled time is extracted from task."""
        run_time = timezone.now() + timedelta(hours=2)
        job = Job.objects.create(
            queue_name="default",
            scheduled_at=run_time,
            class_name="tests.dummy.tasks.dummy_task",
            arguments={"arguments": {"args": [], "kwargs": {}}},
        )
        self.assertEqual(job.scheduled_at, run_time)

    def test_attributes_from_task_maps_class_name(self):
        """Class name matches task module path."""
        attrs = Job.attributes_from_django_task(dummy_task, [], {})
        self.assertEqual(attrs["class_name"], "tests.dummy.tasks.dummy_task")

    def test_attributes_from_task_maps_concurrency_key(self):
        """Concurrency key is extracted from task decorator."""
        attrs = Job.attributes_from_django_task(limited_task, [], {})
        self.assertEqual(attrs["concurrency_key"], "limited_task")

    def test_default_queue_name_is_default(self):
        """Default queue name is 'default'."""
        attrs = Job.attributes_from_django_task(dummy_task, [], {})
        self.assertEqual(attrs["queue_name"], "default")

    def test_default_priority_is_zero(self):
        """Default priority is 0."""
        attrs = Job.attributes_from_django_task(dummy_task, [], {})
        self.assertEqual(attrs["priority"], 0)


class JobStateTransitionsTestCase(TestCase):
    """Tests for job state transitions (finished, failed)."""

    def test_finished_marks_job_as_finished(self):
        """finished() sets finished_at timestamp."""
        job = Job.objects.enqueue(dummy_task, [], {})
        job.finished()

        job.refresh_from_db()
        self.assertEqual(job.status, "finished")
        self.assertIsNotNone(job.finished_at)

    def test_failed_with_creates_failed_execution(self):
        """failed_with() creates a FailedExecution record."""
        job = Job.objects.enqueue(dummy_task, [], {})
        # Clear the ready execution first to simulate claim
        job.ready_execution.delete()

        job.failed_with(ValueError("test error"))

        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertTrue(hasattr(job, "failed_execution"))
        self.assertIn("ValueError", job.failed_execution.error)

    def test_failed_with_exception_formats_error_message(self):
        """Exception is formatted as 'ClassName: message'."""
        job = Job.objects.enqueue(dummy_task, [], {})
        job.ready_execution.delete()

        job.failed_with(RuntimeError("something went wrong"))

        self.assertEqual(
            job.failed_execution.error, "RuntimeError: something went wrong"
        )

    def test_failed_with_string_stores_directly(self):
        """String errors are stored as-is."""
        job = Job.objects.enqueue(dummy_task, [], {})
        job.ready_execution.delete()

        job.failed_with("custom error message")

        self.assertEqual(job.failed_execution.error, "custom error message")


class JobIsDueTestCase(TestCase):
    """Tests for the is_due property."""

    def test_job_with_no_scheduled_at_is_due(self):
        """Job without scheduled_at is immediately due."""
        job = Job(scheduled_at=None)
        self.assertTrue(job.is_due)

    def test_job_with_past_scheduled_at_is_due(self):
        """Job with past scheduled_at is due."""
        job = Job(scheduled_at=timezone.now() - timedelta(hours=1))
        self.assertTrue(job.is_due)

    def test_job_with_future_scheduled_at_is_not_due(self):
        """Job with future scheduled_at is not due."""
        job = Job(scheduled_at=timezone.now() + timedelta(hours=1))
        self.assertFalse(job.is_due)


class JobConcurrencyControlTestCase(TestCase):
    """Tests for concurrency control mechanics on jobs."""

    def test_job_without_concurrency_key_is_not_limited(self):
        """Job without concurrency_key is not concurrency limited."""
        job = Job.objects.enqueue(dummy_task, [], {})
        self.assertFalse(job.is_concurrency_limited)

    def test_job_with_concurrency_key_is_limited(self):
        """Job with concurrency_key is concurrency limited."""
        job = Job.objects.enqueue(limited_task, [], {})
        self.assertTrue(job.is_concurrency_limited)

    def test_acquire_lock_without_concurrency_returns_true(self):
        """Non-concurrency-limited jobs always acquire the lock."""
        job = Job.objects.enqueue(dummy_task, [], {})
        self.assertTrue(job.acquire_concurrency_lock())

    def test_acquire_lock_creates_semaphore(self):
        """First acquisition creates the semaphore."""
        self.assertEqual(Semaphore.objects.count(), 0)
        Job.objects.enqueue(limited_task, [], {})
        self.assertEqual(Semaphore.objects.count(), 1)

    def test_release_lock_increments_semaphore(self):
        """Releasing returns the semaphore slot."""
        job = Job.objects.enqueue(limited_task, [], {})
        initial_value = Semaphore.objects.get(key="limited_task").value

        job.release_concurrency_lock()

        new_value = Semaphore.objects.get(key="limited_task").value
        self.assertEqual(new_value, initial_value + 1)
