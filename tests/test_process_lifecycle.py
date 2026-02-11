from datetime import timedelta
from unittest.mock import MagicMock

from django.test import TestCase
from django.utils import timezone

import steady_queue
from steady_queue.models import (
    ClaimedExecution,
    FailedExecution,
    Job,
    Process,
    ReadyExecution,
)
from tests.dummy.tasks import dummy_task


class TestHelperMixin:
    """Helper methods for creating test data."""

    @classmethod
    def create_process(
        cls, name="test-worker", kind="worker", supervisor=None, **kwargs
    ):
        return Process.objects.create(
            name=name,
            kind=kind,
            pid=kwargs.get("pid", 12345),
            hostname=kwargs.get("hostname", "test-host"),
            last_heartbeat_at=kwargs.get("last_heartbeat_at", timezone.now()),
            supervisor=supervisor,
        )

    @classmethod
    def create_claimed_execution(cls, process):
        """Create a job and claim it for the given process."""
        job = Job.objects.enqueue(dummy_task, [], {})
        ReadyExecution.objects.claim(queue_list=["*"], limit=1, process_id=process.id)
        return ClaimedExecution.objects.get(job=job)


class ProcessDeletionReleasesClaimedExecutionsTest(TestHelperMixin, TestCase):
    """
    Regression: in solid_queue, Process has an after_destroy callback that
    releases all claimed executions back to the ready queue. In our port,
    on_delete=SET_NULL just orphaned them instead.
    """

    def test_deleting_process_releases_claimed_executions_to_ready(self):
        """When a worker Process is deleted, its claimed executions should
        be released back to the ready queue (not orphaned)."""
        process = self.create_process(name="worker-1")
        self.create_claimed_execution(process)
        self.create_claimed_execution(process)

        self.assertEqual(ClaimedExecution.objects.count(), 2)
        self.assertEqual(ReadyExecution.objects.count(), 0)

        process.delete()

        # Executions should be re-dispatched, not orphaned
        self.assertEqual(ClaimedExecution.objects.count(), 0)
        self.assertEqual(ReadyExecution.objects.count(), 2)

    def test_deleting_non_worker_process_does_not_release_executions(self):
        """Only worker processes should release claimed executions."""
        process = self.create_process(name="dispatcher-1", kind="dispatcher")

        # Dispatcher won't have claimed executions, but verify no error
        process.delete()
        self.assertEqual(Process.objects.count(), 0)

    def test_pruning_process_fails_claimed_executions(self):
        """When a process is pruned, its claimed executions should be
        failed (not just orphaned with null process_id)."""
        process = self.create_process(
            name="stale-worker",
            last_heartbeat_at=timezone.now()
            - steady_queue.process_alive_threshold
            - timedelta(minutes=1),
        )
        self.create_claimed_execution(process)
        self.create_claimed_execution(process)

        self.assertEqual(ClaimedExecution.objects.count(), 2)

        Process.objects.prune()

        # Pruning should fail the executions, not orphan them
        self.assertEqual(ClaimedExecution.objects.count(), 0)
        self.assertEqual(FailedExecution.objects.count(), 2)
        self.assertEqual(Process.objects.count(), 0)

    def test_no_orphaned_executions_after_process_deletion(self):
        """There should be no claimed executions with process_id=NULL
        after a process is deleted."""
        process = self.create_process(name="worker-1")
        self.create_claimed_execution(process)

        process.delete()

        orphaned = ClaimedExecution.objects.filter(process_id=None)
        self.assertEqual(orphaned.count(), 0)


class PruneDeadProcessesNilSafeTest(TestHelperMixin, TestCase):
    """
    Regression: prune_dead_processes crashed with AttributeError when
    self.process was None because it accessed self.process.pk.
    """

    def test_prune_excluding_none_does_not_crash(self):
        """Pruning with excluding=None should work (prune all stale)."""
        self.create_process(
            name="stale-worker",
            last_heartbeat_at=timezone.now()
            - steady_queue.process_alive_threshold
            - timedelta(minutes=1),
        )
        active = self.create_process(
            name="active-worker",
            last_heartbeat_at=timezone.now(),
        )

        # This mirrors what happens when supervisor's self.process is None
        Process.objects.prune(excluding=None)

        self.assertEqual(Process.objects.count(), 1)
        self.assertEqual(Process.objects.first().id, active.id)

    def test_prune_excluding_specific_process(self):
        """Pruning excluding a specific process should skip it."""
        supervisor = self.create_process(
            name="supervisor",
            kind="supervisor",
            last_heartbeat_at=timezone.now(),
        )
        self.create_process(
            name="stale-worker",
            last_heartbeat_at=timezone.now()
            - steady_queue.process_alive_threshold
            - timedelta(minutes=1),
        )

        Process.objects.prune(excluding=supervisor)

        self.assertEqual(Process.objects.count(), 1)
        self.assertEqual(Process.objects.first().id, supervisor.id)


class HeartbeatNilGuardTest(TestHelperMixin, TestCase):
    """
    Regression: after self.process was set to None on the first heartbeat
    failure, subsequent heartbeat() calls crashed with
    AttributeError: 'NoneType' object has no attribute 'heartbeat'.
    """

    def test_heartbeat_with_nil_process_does_not_crash(self):
        """heartbeat() should be a no-op when self.process is None."""
        from steady_queue.processes.registrable import Registrable

        # Create a minimal object that has the Registrable.heartbeat method
        obj = type(
            "FakeProcess",
            (),
            {
                "process": None,
                "name": "test-worker",
                "heartbeat": Registrable.heartbeat,
            },
        )()

        # Should not raise — heartbeat should be a no-op when process is None
        obj.heartbeat()

    def test_heartbeat_sets_process_to_none_on_not_found(self):
        """If the Process record is deleted, heartbeat should set
        self.process = None and not crash on subsequent calls."""
        process = self.create_process(name="ephemeral-worker")
        process_id = process.id

        # Delete the record from the DB to simulate pruning
        Process.objects.filter(id=process_id).delete()

        from steady_queue.processes.registrable import Registrable

        obj = type(
            "FakeProcess",
            (),
            {
                "process": process,  # stale reference
                "name": "test-worker",
                "heartbeat": Registrable.heartbeat,
                "wake_up": lambda self: None,
            },
        )()

        # First heartbeat should catch DoesNotExist and set process to None
        obj.heartbeat()
        self.assertIsNone(obj.process)

        # Second heartbeat should be a no-op, not crash
        obj.heartbeat()


class ClaimExecutionsNilProcessGuardTest(TestHelperMixin, TestCase):
    """
    Regression: when self.process was None, claim_executions passed
    process_id=None, creating orphaned ClaimedExecution records.
    """

    def test_claim_with_none_process_id_returns_empty(self):
        """claim() should return an empty list when process_id is None."""
        Job.objects.enqueue(dummy_task, [], {})
        Job.objects.enqueue(dummy_task, [], {})

        claimed = ReadyExecution.objects.claim(
            queue_list=["*"], limit=10, process_id=None
        )

        # Should refuse to claim rather than create orphaned executions
        self.assertEqual(len(claimed), 0)
        # Ready executions should remain untouched
        self.assertEqual(ReadyExecution.objects.count(), 2)
        self.assertEqual(ClaimedExecution.objects.count(), 0)


class DeregisterOrderingTest(TestHelperMixin, TestCase):
    """
    Regression: solid_queue calls destroy! on self first (triggering
    after_destroy callbacks), then deregisters supervisees. Our port
    did the reverse.
    """

    def test_deregister_releases_own_claimed_executions(self):
        """Deregistering a worker process should release its claimed
        executions."""
        process = self.create_process(name="worker-1")
        self.create_claimed_execution(process)

        self.assertEqual(ClaimedExecution.objects.count(), 1)

        process.deregister()

        self.assertEqual(ClaimedExecution.objects.count(), 0)
        self.assertEqual(Process.objects.count(), 0)

    def test_deregister_supervisor_cascades_to_supervisees(self):
        """Deregistering a supervisor should also deregister its
        supervisees and release their claimed executions."""
        supervisor = self.create_process(name="supervisor-1", kind="supervisor")
        worker = self.create_process(
            name="worker-1", kind="worker", supervisor=supervisor
        )
        self.create_claimed_execution(worker)

        self.assertEqual(Process.objects.count(), 2)
        self.assertEqual(ClaimedExecution.objects.count(), 1)

        supervisor.deregister()

        self.assertEqual(Process.objects.count(), 0)
        self.assertEqual(ClaimedExecution.objects.count(), 0)


class PoolPostNilProcessTest(TestCase):
    """
    Regression: Pool.post accessed execution.process.name for logging
    after perform(), which crashed when execution.process was None.
    solid_queue's Pool does not access execution.process at all.
    """

    def test_pool_post_does_not_access_execution_process(self):
        """Pool.post should not crash when execution.process is None."""
        import time

        from steady_queue.processes.pool import Pool

        pool = Pool(size=1, on_idle=lambda: None)

        execution = MagicMock()
        execution.process = None
        execution.job_id = 1
        execution.job.class_name = "test_task"
        execution.pk = 1

        # Should not raise AttributeError
        pool.post(execution)
        # Give the thread pool time to execute
        time.sleep(0.2)
        pool.shutdown()

        # Verify perform was called successfully
        execution.perform.assert_called_once()
