from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless

from django.db import connections, transaction
from django.test import TransactionTestCase

from steady_queue.app_executor import AppExecutor
from tests.dummy.models import Dummy


@skipUnless(
    connections["default"].vendor == "postgresql",
    "Requires PostgreSQL application connection pooling",
)
class AppExecutorConnectionsTest(TransactionTestCase):
    databases = {"default", "queue"}

    def setUp(self):
        self.application = connections["default"]
        self.application.close()
        self.application.close_pool()
        self.original_options = self.application.settings_dict["OPTIONS"]
        self.application.settings_dict["OPTIONS"] = {
            **self.original_options,
            "pool": {"min_size": 0, "max_size": 1, "timeout": 0.25},
        }
        self.addCleanup(self.restore_application_pool)

    def restore_application_pool(self):
        self.application.close()
        self.application.close_pool()
        self.application.settings_dict["OPTIONS"] = self.original_options

    @staticmethod
    def perform_task(*, fail=False):
        with AppExecutor.wrap_in_app_executor():
            Dummy.objects.count()
            if fail:
                raise ValueError("Task failed")
        return (
            connections["default"].connection is None,
            connections["queue"].connection is None,
        )

    def assert_pool_reusable_by_another_worker(self, *, fail=False):
        # Keep both threads alive: ending a thread must not stand in for the
        # per-task cleanup that long-lived worker threads need.
        workers = [ThreadPoolExecutor(max_workers=1) for _ in range(2)]
        try:
            first = workers[0].submit(self.perform_task, fail=fail)
            if fail:
                with self.assertRaisesMessage(ValueError, "Task failed"):
                    first.result(timeout=5)
            else:
                first.result(timeout=5)

            # A leaked application connection leaves this separate thread
            # unable to borrow the only connection in the application pool.
            state = workers[1].submit(self.perform_task).result(timeout=5)
            self.assertEqual(state, (True, True))
            self.assertEqual(self.application.pool.get_stats()["pool_available"], 1)
        finally:
            for worker in workers:
                worker.submit(connections.close_all).result(timeout=5)
                worker.shutdown()

    def test_success_returns_application_connection_for_other_workers(self):
        self.assert_pool_reusable_by_another_worker()

    def test_failure_returns_application_connection_for_other_workers(self):
        self.assert_pool_reusable_by_another_worker(fail=True)

    def test_main_thread_preserves_callers_connections_and_transaction(self):
        connections["queue"].ensure_connection()
        queue_connection = connections["queue"].connection
        with transaction.atomic():
            Dummy.objects.count()
            application_connection = self.application.connection
            with AppExecutor.wrap_in_app_executor():
                Dummy.objects.count()
            self.assertIs(self.application.connection, application_connection)
            self.assertIs(connections["queue"].connection, queue_connection)
            self.assertTrue(self.application.in_atomic_block)
            Dummy.objects.count()
