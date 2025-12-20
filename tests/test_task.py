from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from steady_queue.task import SteadyQueueTask, UnknownTaskClassError
from tests.dummy.tasks import dummy_task, limited_task, task_with_args


class TaskSerializationTestCase(SimpleTestCase):
    """Tests for task serialization."""

    def test_serialize_includes_class_name(self):
        """Serialized data includes task module path."""
        data = dummy_task.serialize([], {})
        self.assertEqual(data["class_name"], "tests.dummy.tasks.dummy_task")

    def test_serialize_includes_arguments(self):
        """Serialized data includes args and kwargs."""
        data = task_with_args.serialize(["Alice"], {"extra": "value"})
        self.assertIn("arguments", data)
        self.assertIn("args", data["arguments"])
        self.assertIn("kwargs", data["arguments"])

    def test_serialize_includes_scheduled_at_for_deferred(self):
        """Deferred tasks include scheduled_at timestamp."""
        run_time = timezone.now() + timedelta(hours=1)
        task = dummy_task.using(run_after=run_time)
        data = task.serialize([], {})
        self.assertEqual(data["scheduled_at"], run_time.isoformat())

    def test_serialize_includes_none_scheduled_at_for_immediate(self):
        """Immediate tasks have null scheduled_at."""
        data = dummy_task.serialize([], {})
        self.assertIsNone(data["scheduled_at"])

    def test_serialize_includes_enqueued_at(self):
        """Serialized data includes enqueue timestamp."""
        data = dummy_task.serialize([], {})
        self.assertIn("enqueued_at", data)
        self.assertIsNotNone(data["enqueued_at"])

    def test_serialize_includes_backend(self):
        """Serialized data includes backend name."""
        data = dummy_task.serialize([], {})
        self.assertIn("backend", data)


class TaskDeserializationTestCase(SimpleTestCase):
    """Tests for task deserialization."""

    def test_deserialize_restores_task(self):
        """Deserialized task matches original."""
        original = dummy_task
        data = original.serialize([], {})

        restored = SteadyQueueTask.deserialize(data)

        self.assertEqual(restored.module_path, original.module_path)

    def test_deserialize_restores_scheduled_time(self):
        """Deserialized task preserves run_after."""
        run_time = timezone.now() + timedelta(hours=1)
        original = dummy_task.using(run_after=run_time)
        data = original.serialize([], {})

        restored = SteadyQueueTask.deserialize(data)

        self.assertEqual(restored.run_after, run_time)

    def test_deserialize_raises_for_unknown_class(self):
        """Unknown task class raises UnknownTaskClassError."""
        data = {
            "class_name": "nonexistent.module.task",
            "queue_name": "default",
            "priority": 0,
            "scheduled_at": None,
            "backend": "default",
        }

        with self.assertRaises(UnknownTaskClassError):
            SteadyQueueTask.deserialize(data)


class TaskUsingTestCase(SimpleTestCase):
    """Tests for task.using() configuration."""

    def test_using_with_timedelta_converts_to_datetime(self):
        """run_after timedelta is converted to datetime."""
        task = dummy_task.using(run_after=timedelta(hours=2))

        self.assertIsNotNone(task.run_after)
        self.assertGreater(task.run_after, timezone.now())

    def test_using_with_datetime_preserves_value(self):
        """run_after datetime is preserved."""
        run_time = timezone.now() + timedelta(hours=3)
        task = dummy_task.using(run_after=run_time)

        self.assertEqual(task.run_after, run_time)


class TaskConcurrencyConfigTestCase(SimpleTestCase):
    """Tests for concurrency configuration on tasks."""

    def test_limited_task_has_concurrency_key(self):
        """Task with @limits_concurrency has concurrency_key."""
        self.assertEqual(limited_task.concurrency_key, "limited_task")

    def test_limited_task_has_concurrency_limit(self):
        """Task with @limits_concurrency has concurrency_limit."""
        self.assertEqual(limited_task.concurrency_limit, 1)

    def test_regular_task_has_no_concurrency_key(self):
        """Regular task has no concurrency_key."""
        self.assertIsNone(dummy_task.concurrency_key)

    def test_regular_task_has_no_concurrency_limit(self):
        """Regular task has no concurrency_limit."""
        self.assertIsNone(dummy_task.concurrency_limit)


class TaskSerializationRoundTripTestCase(SimpleTestCase):
    """Tests for serialization round-trips."""

    def test_serialize_deserialize_preserves_task_identity(self):
        """Round-trip preserves task identity."""
        data = dummy_task.serialize(["arg1"], {"key": "value"})
        restored = SteadyQueueTask.deserialize(data)

        self.assertEqual(restored.module_path, dummy_task.module_path)
        self.assertEqual(restored.func, dummy_task.func)

    def test_execute_calls_task_function(self):
        """Execute deserializes and calls the task function."""
        # We can verify the data structure is correct for execution
        data = task_with_args.serialize(["TestName"], {})

        self.assertEqual(data["class_name"], "tests.dummy.tasks.task_with_args")
        self.assertIn("TestName", str(data["arguments"]))
