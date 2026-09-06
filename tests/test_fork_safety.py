from unittest import skipUnless
from unittest.mock import patch

from django.db import connections
from django.test import SimpleTestCase, TransactionTestCase

from steady_queue.configuration import Configuration
from steady_queue.models import (
    ClaimedExecution,
    FailedExecution,
    Job,
    Process,
    ReadyExecution,
)
from steady_queue.processes.base import Base
from steady_queue.processes.supervisor import Supervisor
from tests.dummy.tasks import dummy_task


class SupervisorForkSafetyTest(SimpleTestCase):
    def build_supervisor(self) -> Supervisor:
        options = Configuration.Options(
            workers=[],
            dispatchers=[],
            recurring_tasks=[],
            skip_recurring=True,
        )
        return Supervisor(Configuration(options))

    def test_supervisor_start_resets_connections_before_forking(self):
        supervisor = self.build_supervisor()
        calls = []

        supervisor.boot = lambda: calls.append("boot")
        supervisor.reset_database_connections = lambda: calls.append("reset")
        supervisor.start_processes = lambda: calls.append("start_processes")
        supervisor.launch_maintenance_task = lambda: calls.append("launch_maintenance")
        supervisor.supervise = lambda: calls.append("supervise")

        supervisor.start()

        self.assertEqual(
            calls,
            [
                "boot",
                "reset",
                "start_processes",
                "launch_maintenance",
                "supervise",
            ],
        )


@skipUnless(
    connections["queue"].vendor == "postgresql",
    "Requires PostgreSQL connection pooling on the queue database",
)
class SupervisorPostgreSQLForkTest(TransactionTestCase):
    databases = {"default", "queue"}

    def setUp(self):
        options = Configuration.Options(
            workers=[], dispatchers=[], recurring_tasks=[], skip_recurring=True
        )
        self.supervisor = Supervisor(Configuration(options))
        self.supervisor.register()
        self.worker_config = Configuration.Process(
            kind="worker", attributes=Configuration.Worker()
        )
        self.connection = connections["queue"]
        self.pool_options = self.connection.settings_dict["OPTIONS"]["pool"].copy()
        self.addCleanup(self.supervisor.reset_database_connections)

    def assert_reset_at_fork(self):
        # Intercept only the OS fork; exercise real Django connections, psycopg
        # pools, and replacement recovery up to the boundary children inherit.
        self.assertIsNone(self.connection.connection)
        self.assertEqual(self.connection.__class__._connection_pools, {})
        self.assertEqual(
            self.connection.settings_dict["OPTIONS"]["pool"], self.pool_options
        )
        return 12346

    def test_start_process_resets_open_connection_and_pool_before_fork(self):
        self.assertIsNotNone(self.connection.connection)
        self.assertIn("queue", self.connection.__class__._connection_pools)

        with patch(
            "steady_queue.processes.supervisor.os.fork",
            side_effect=self.assert_reset_at_fork,
        ) as fork:
            self.supervisor.start_process(self.worker_config)

        fork.assert_called_once_with()
        self.assertIn(12346, self.supervisor.forks)
        # Pooling remains usable by the parent after the reset.
        self.assertTrue(Process.objects.filter(pk=self.supervisor.process.pk).exists())
        self.assertIn("queue", self.connection.__class__._connection_pools)

    def test_replacement_resets_connection_reopened_by_job_recovery(self):
        old_worker = self.worker_config.instantiate()
        self.addCleanup(old_worker.pool.shutdown)
        registered_worker = Process.register(
            kind="worker",
            name=old_worker.name,
            pid=12345,
            hostname="test-host",
            supervisor=self.supervisor.process,
        )
        job = Job.objects.enqueue(dummy_task, [], {})
        ReadyExecution.objects.claim(["*"], 1, registered_worker.pk)
        self.supervisor.forks[12345] = old_worker
        self.supervisor.configured_processes[12345] = self.worker_config
        self.supervisor.reset_database_connections()

        with patch(
            "steady_queue.processes.supervisor.os.fork",
            side_effect=self.assert_reset_at_fork,
        ) as fork:
            self.supervisor.replace_fork(12345, 11)

        fork.assert_called_once_with()
        self.assertNotIn(12345, self.supervisor.forks)
        self.assertIn(12346, self.supervisor.forks)
        self.assertFalse(ClaimedExecution.objects.filter(job=job).exists())
        self.assertTrue(FailedExecution.objects.filter(job=job).exists())


class ResetDatabaseConnectionsTest(SimpleTestCase):
    def test_reset_connections_clears_psycopg_pool_cache_without_disabling_pooling(
        self,
    ):
        class FakePool:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        class FakeConnection:
            _connection_pools = {}

            def __init__(self, engine: str):
                self.settings_dict = {
                    "ENGINE": engine,
                    "OPTIONS": {"pool": {"min_size": 1, "max_size": 4}},
                }

        class FakeConnections(dict):
            close_all_called = False

            def __iter__(self):
                return iter(self.keys())

            def close_all(self):
                self.close_all_called = True

        pool_default = FakePool()
        pool_queue = FakePool()
        FakeConnection._connection_pools = {
            "default": pool_default,
            "queue": pool_queue,
        }

        fake_connections = FakeConnections(
            {
                "default": FakeConnection("django.db.backends.postgresql"),
                "queue": FakeConnection("django.db.backends.postgresql"),
                "sqlite": FakeConnection("django.db.backends.sqlite3"),
            }
        )

        with patch("steady_queue.processes.base.connections", fake_connections):
            Base().reset_database_connections()

        self.assertIn("pool", fake_connections["default"].settings_dict["OPTIONS"])
        self.assertIn("pool", fake_connections["queue"].settings_dict["OPTIONS"])
        self.assertIn("pool", fake_connections["sqlite"].settings_dict["OPTIONS"])

        self.assertTrue(fake_connections.close_all_called)
        self.assertTrue(pool_default.closed)
        self.assertTrue(pool_queue.closed)
        self.assertEqual(FakeConnection._connection_pools, {})
