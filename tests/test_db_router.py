from unittest.mock import patch

from django.test import SimpleTestCase

import steady_queue
from steady_queue.db_router import SteadyQueueRouter, steady_queue_database_alias
from steady_queue.models import Job


class SteadyQueueRouterTests(SimpleTestCase):
    def test_alias_from_module_attribute(self):
        with patch.object(steady_queue, "database", "custom_db"):
            self.assertEqual(steady_queue_database_alias(), "custom_db")

    def test_alias_default_fallback(self):
        with patch.object(steady_queue, "database", "default"):
            self.assertEqual(steady_queue_database_alias(), "default")

    def test_db_for_read_write(self):
        router = SteadyQueueRouter()
        with patch.object(steady_queue, "database", "queue_db"):
            self.assertEqual(router.db_for_read(Job), "queue_db")
            self.assertEqual(router.db_for_write(Job), "queue_db")

    def test_allow_migrate_only_on_alias(self):
        router = SteadyQueueRouter()
        with patch.object(steady_queue, "database", "queue_db"):
            self.assertTrue(router.allow_migrate("queue_db", "steady_queue", "job"))
            self.assertFalse(router.allow_migrate("default", "steady_queue", "job"))
            # other apps should not migrate on the steady_queue database
            self.assertFalse(router.allow_migrate("queue_db", "auth", "user"))
            self.assertIsNone(router.allow_migrate("default", "auth", "user"))
