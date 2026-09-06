import os
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from steady_queue.configuration import Configuration
from steady_queue.models import Job, Queue
from steady_queue.processes.base import Base
from steady_queue.processes.runnable import Runnable
from steady_queue.processes.supervisor import Supervisor
from steady_queue.signals import (
    ProcessLifecycle,
    QueueLifecycle,
    process_restarted,
    process_started,
    process_stopped,
    queue_paused,
    queue_resumed,
)
from tests.dummy.tasks import dummy_task


class FakeRunnable(Runnable, Base):
    mode = "inline"

    def run(self):
        pass


class ProcessLifecycleSignalTests(SimpleTestCase):
    def test_runnable_emits_started_and_stopped_with_operational_context(self):
        process = FakeRunnable()
        started = MagicMock()
        stopped = MagicMock()

        process_started.connect(started)
        process_stopped.connect(stopped)
        self.addCleanup(process_started.disconnect, started)
        self.addCleanup(process_stopped.disconnect, stopped)

        process.start()

        started.assert_called_once_with(
            signal=process_started,
            sender=ProcessLifecycle,
            process_kind="fakerunnable",
            process_name=process.name,
            pid=process.pid,
            hostname=process.hostname,
            metadata={},
        )
        stopped.assert_called_once_with(
            signal=process_stopped,
            sender=ProcessLifecycle,
            process_kind="fakerunnable",
            process_name=process.name,
            pid=process.pid,
            hostname=process.hostname,
            metadata={},
            error=None,
        )

    def test_stopped_signal_includes_run_error(self):
        process = FakeRunnable()
        error = RuntimeError("broken")
        stopped = MagicMock()
        process.run = MagicMock(side_effect=error)

        process_stopped.connect(stopped)
        self.addCleanup(process_stopped.disconnect, stopped)

        with self.assertRaises(RuntimeError):
            process.start()

        self.assertIs(stopped.call_args.kwargs["error"], error)

    def test_forked_child_does_not_emit_supervisor_stopped(self):
        supervisor = Supervisor(Configuration(Configuration.Options()))
        originating_pid = os.getpid()
        read_fd, write_fd = os.pipe()
        child_pids = []

        def record_stop(**kwargs):
            message = f"{os.getpid()}:{kwargs['pid']}\n".encode()
            os.write(write_fd, message)

        def fork_child():
            pid = os.fork()
            if pid == 0:
                os.close(read_fd)
                raise SystemExit
            child_pids.append(pid)

        process_stopped.connect(record_stop)
        try:
            with (
                patch.object(supervisor, "boot"),
                patch.object(supervisor, "reset_database_connections"),
                patch.object(supervisor, "start_processes", side_effect=fork_child),
                patch.object(supervisor, "launch_maintenance_task"),
                patch.object(supervisor, "restore_default_signal_handlers"),
                patch.object(supervisor, "shutdown"),
                patch.object(supervisor, "supervise"),
            ):
                supervisor.start()

            if os.getpid() != originating_pid:
                os.close(write_fd)
                os._exit(0)

            os.waitpid(child_pids[0], 0)
            os.close(write_fd)
            write_fd = None
            records = os.read(read_fd, 4096).decode().splitlines()
        finally:
            process_stopped.disconnect(record_stop)
            os.close(read_fd)
            if write_fd is not None:
                os.close(write_fd)

        self.assertEqual(records, [f"{originating_pid}:{originating_pid}"])

    def test_supervisor_emits_restart_after_replacing_child(self):
        supervisor = Supervisor(Configuration(Configuration.Options()))
        terminated = FakeRunnable()
        configured = MagicMock()
        supervisor.forks[123] = terminated
        supervisor.configured_processes[123] = configured
        restarted = MagicMock()

        process_restarted.connect(restarted)
        self.addCleanup(process_restarted.disconnect, restarted)

        with (
            patch.object(supervisor, "handle_claimed_jobs_by"),
            patch.object(supervisor, "start_process", return_value=456),
        ):
            supervisor.replace_fork(123, 9)

        restarted.assert_called_once_with(
            signal=process_restarted,
            sender=ProcessLifecycle,
            process_kind="fakerunnable",
            process_name=terminated.name,
            pid=123,
            hostname=terminated.hostname,
            metadata={},
            exitcode=9,
            replacement_pid=456,
            supervisor_pid=supervisor.pid,
        )


class QueueLifecycleSignalTests(TestCase):
    databases = {"default", "queue"}

    def setUp(self):
        Job.objects.enqueue(dummy_task, [], {})
        self.queue = Queue.objects.get(queue_name="default")

    def test_pause_and_resume_report_real_and_idempotent_actions(self):
        paused = MagicMock()
        resumed = MagicMock()
        queue_paused.connect(paused)
        queue_resumed.connect(resumed)
        self.addCleanup(queue_paused.disconnect, paused)
        self.addCleanup(queue_resumed.disconnect, resumed)

        self.queue.pause()
        self.queue.pause()
        self.queue.resume()
        self.queue.resume()

        self.assertEqual(
            [call.kwargs["changed"] for call in paused.call_args_list], [True, False]
        )
        self.assertEqual(
            [call.kwargs["changed"] for call in resumed.call_args_list], [True, False]
        )
        self.assertTrue(
            all(
                call.kwargs["queue_name"] == "default" for call in paused.call_args_list
            )
        )
        self.assertTrue(
            all("queue" not in call.kwargs for call in paused.call_args_list)
        )
        self.assertTrue(
            all("queue" not in call.kwargs for call in resumed.call_args_list)
        )
        self.assertTrue(
            all(
                call.kwargs["sender"] is QueueLifecycle
                for call in paused.call_args_list
            )
        )
        self.assertTrue(
            all(
                call.kwargs["sender"] is QueueLifecycle
                for call in resumed.call_args_list
            )
        )
