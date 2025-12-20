from django.tasks import TaskResultStatus
from django.test import TestCase
from django.utils import timezone

from steady_queue.models import Job, Process, ReadyExecution
from tests.dummy.tasks import dummy_task, task_with_args


class BackendEnqueueTestCase(TestCase):
    """Tests for backend.enqueue()."""

    def test_enqueue_creates_job(self):
        """enqueue() should create a Job in the database."""
        backend = dummy_task.get_backend()

        backend.enqueue(dummy_task, [], {})

        self.assertEqual(Job.objects.count(), 1)

    def test_enqueue_returns_task_result(self):
        """enqueue() should return a TaskResult with the Job ID."""
        backend = dummy_task.get_backend()

        result = backend.enqueue(dummy_task, [], {})

        self.assertEqual(result.id, str(Job.objects.get().id))

    def test_enqueue_task_result_has_ready_status(self):
        """Newly enqueued immediate task should have READY status."""
        backend = dummy_task.get_backend()

        result = backend.enqueue(dummy_task, [], {})

        self.assertEqual(result.status, TaskResultStatus.READY)

    def test_enqueue_with_args_stores_arguments(self):
        """enqueue() should store task arguments."""
        backend = task_with_args.get_backend()

        result = backend.enqueue(task_with_args, ["Alice"], {"greeting": "Hello"})

        job = Job.objects.get(id=result.id)
        self.assertIn("Alice", str(job.arguments))
        self.assertIn("Hello", str(job.arguments))

    def test_enqueue_stores_task_reference(self):
        """enqueue() should store reference to the original task."""
        backend = dummy_task.get_backend()

        result = backend.enqueue(dummy_task, [], {})

        self.assertEqual(result.task.module_path, dummy_task.module_path)


class BackendTaskResultTestCase(TestCase):
    """Tests for to_task_result() mapping."""

    def test_to_task_result_maps_finished_status(self):
        """Finished job should map to SUCCESSFUL status."""
        backend = dummy_task.get_backend()
        job = Job.objects.enqueue(dummy_task, [], {})
        job.finished()
        job.refresh_from_db()

        result = backend.to_task_result(dummy_task, job, [], {})

        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)

    def test_to_task_result_maps_failed_status(self):
        """Failed job should map to FAILED status."""
        backend = dummy_task.get_backend()
        job = Job.objects.enqueue(dummy_task, [], {})
        job.ready_execution.delete()
        job.failed_with("error")
        job.refresh_from_db()

        result = backend.to_task_result(dummy_task, job, [], {})

        self.assertEqual(result.status, TaskResultStatus.FAILED)

    def test_to_task_result_maps_claimed_status(self):
        """Claimed job should map to RUNNING status."""
        # Create a process for claiming
        process = Process.objects.create(
            name="test-worker",
            kind="Worker",
            pid=12345,
            hostname="test-host",
            last_heartbeat_at=timezone.now(),
        )

        backend = dummy_task.get_backend()
        job = Job.objects.enqueue(dummy_task, [], {})
        # Claim the job
        ReadyExecution.objects.claim(queue_list=["*"], limit=1, process_id=process.id)
        job.refresh_from_db()

        result = backend.to_task_result(dummy_task, job, [], {})

        self.assertEqual(result.status, TaskResultStatus.RUNNING)

    def test_to_task_result_includes_enqueued_at(self):
        """Task result should include enqueue timestamp."""
        backend = dummy_task.get_backend()
        job = Job.objects.enqueue(dummy_task, [], {})

        result = backend.to_task_result(dummy_task, job, [], {})

        self.assertIsNotNone(result.enqueued_at)


class BackendCapabilitiesTestCase(TestCase):
    """Tests for backend capability flags."""

    def test_supports_defer(self):
        """Backend should support deferred tasks."""
        backend = dummy_task.get_backend()
        self.assertTrue(backend.supports_defer)

    def test_does_not_support_async(self):
        """Backend should not support async tasks."""
        backend = dummy_task.get_backend()
        self.assertFalse(backend.supports_async_task)

    def test_does_not_support_get_result(self):
        """Backend should not support result retrieval."""
        backend = dummy_task.get_backend()
        self.assertFalse(backend.supports_get_result)

    def test_get_result_raises_not_implemented(self):
        """get_result() should raise NotImplementedError."""
        backend = dummy_task.get_backend()

        with self.assertRaises(NotImplementedError):
            backend.get_result("some-id")
