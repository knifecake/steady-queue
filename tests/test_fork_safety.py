import warnings
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from steady_queue.configuration import Configuration
from steady_queue.processes.base import Base
from steady_queue.processes.supervisor import Supervisor


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


class ResetDatabaseConnectionsTest(SimpleTestCase):
    def test_reset_connections_disables_and_clears_psycopg_pool_cache(self):
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

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="Overriding setting DATABASES can lead to unexpected behavior.",
                category=UserWarning,
            )

            with self.settings(
                DATABASES={
                    "default": {
                        "ENGINE": "django.db.backends.postgresql",
                        "OPTIONS": {"pool": {"min_size": 1, "max_size": 4}},
                    },
                    "queue": {
                        "ENGINE": "django.db.backends.postgresql",
                        "OPTIONS": {"pool": {"min_size": 1, "max_size": 4}},
                    },
                    "sqlite": {
                        "ENGINE": "django.db.backends.sqlite3",
                        "OPTIONS": {"pool": {"min_size": 1, "max_size": 4}},
                    },
                }
            ):
                with patch("steady_queue.processes.base.connections", fake_connections):
                    Base().reset_database_connections()

                self.assertNotIn("pool", settings.DATABASES["default"]["OPTIONS"])
                self.assertNotIn("pool", settings.DATABASES["queue"]["OPTIONS"])
                self.assertIn("pool", settings.DATABASES["sqlite"]["OPTIONS"])

        self.assertNotIn("pool", fake_connections["default"].settings_dict["OPTIONS"])
        self.assertNotIn("pool", fake_connections["queue"].settings_dict["OPTIONS"])
        self.assertIn("pool", fake_connections["sqlite"].settings_dict["OPTIONS"])

        self.assertTrue(fake_connections.close_all_called)
        self.assertTrue(pool_default.closed)
        self.assertTrue(pool_queue.closed)
        self.assertEqual(FakeConnection._connection_pools, {})
