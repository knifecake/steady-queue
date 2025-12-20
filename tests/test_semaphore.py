from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from steady_queue.models import Job, Semaphore
from tests.dummy.tasks import limited_task


class SemaphoreWaitTestCase(TestCase):
    """Tests for Semaphore.Proxy.wait() behavior."""

    def test_wait_creates_semaphore_on_first_call(self):
        """First wait() should create the semaphore."""
        self.assertEqual(Semaphore.objects.count(), 0)

        Job.objects.enqueue(limited_task, [], {})

        self.assertEqual(Semaphore.objects.count(), 1)
        sem = Semaphore.objects.first()
        self.assertEqual(sem.key, "limited_task")

    def test_wait_decrements_available_semaphore(self):
        """Subsequent wait() should decrement the semaphore value."""
        # Create semaphore with room for 2
        Semaphore.objects.create(key="limited_task", value=2)

        job = Job(
            concurrency_key="limited_task",
            class_name="tests.dummy.tasks.limited_task",
        )
        result = Semaphore.objects.wait(job)

        self.assertTrue(result)
        self.assertEqual(Semaphore.objects.get(key="limited_task").value, 1)

    def test_wait_returns_false_when_exhausted(self):
        """wait() should return False when semaphore is at 0."""
        Semaphore.objects.create(key="limited_task", value=0)

        job = Job(
            concurrency_key="limited_task",
            class_name="tests.dummy.tasks.limited_task",
        )
        result = Semaphore.objects.wait(job)

        self.assertFalse(result)
        self.assertEqual(Semaphore.objects.get(key="limited_task").value, 0)

    def test_wait_sets_expiration(self):
        """wait() should set the expiration time."""
        Job.objects.enqueue(limited_task, [], {})

        sem = Semaphore.objects.get(key="limited_task")
        self.assertIsNotNone(sem.expires_at)
        self.assertGreater(sem.expires_at, timezone.now())


class SemaphoreSignalTestCase(TestCase):
    """Tests for Semaphore.Proxy.signal() behavior."""

    def test_signal_increments_semaphore(self):
        """signal() should increment the semaphore value."""
        Semaphore.objects.create(key="limited_task", value=0)

        job = Job(
            concurrency_key="limited_task",
            class_name="tests.dummy.tasks.limited_task",
        )
        result = Semaphore.objects.signal(job)

        self.assertTrue(result)
        self.assertEqual(Semaphore.objects.get(key="limited_task").value, 1)

    def test_signal_all_increments_multiple(self):
        """signal_all() should increment semaphores for all jobs."""
        Semaphore.objects.create(key="key1", value=0)
        Semaphore.objects.create(key="key2", value=0)

        job1 = Job(concurrency_key="key1", class_name="tests.dummy.tasks.limited_task")
        job2 = Job(concurrency_key="key2", class_name="tests.dummy.tasks.limited_task")

        Semaphore.objects.signal_all([job1, job2])

        self.assertEqual(Semaphore.objects.get(key="key1").value, 1)
        self.assertEqual(Semaphore.objects.get(key="key2").value, 1)


class SemaphoreQuerySetTestCase(TestCase):
    """Tests for Semaphore queryset methods."""

    def test_available_returns_positive_value(self):
        """available() should return semaphores with value > 0."""
        Semaphore.objects.create(key="exhausted", value=0)
        available = Semaphore.objects.create(key="available", value=1)

        self.assertQuerySetEqual(Semaphore.objects.available(), [available])

    def test_expired_returns_past_expiration(self):
        """expired() should return semaphores past their expiration."""
        expired = Semaphore.objects.create(
            key="expired", value=1, expires_at=timezone.now() - timedelta(hours=1)
        )
        Semaphore.objects.create(
            key="not_expired", value=1, expires_at=timezone.now() + timedelta(hours=1)
        )

        self.assertQuerySetEqual(Semaphore.objects.expired(), [expired])

    def test_expired_excludes_null_expiration(self):
        """expired() should not return semaphores with null expiration."""
        Semaphore.objects.create(key="no_expiry", value=1, expires_at=None)

        self.assertQuerySetEqual(Semaphore.objects.expired(), [])


class SemaphoreProxyTestCase(TestCase):
    """Tests for Semaphore.Proxy edge cases."""

    def test_proxy_key_uses_job_concurrency_key(self):
        """Proxy should use the job's concurrency_key."""
        job = Job(concurrency_key="my_key", class_name="tests.dummy.tasks.limited_task")
        proxy = Semaphore.Proxy(job)

        self.assertEqual(proxy.key, "my_key")

    def test_proxy_limit_uses_job_class_limit(self):
        """Proxy should use the job class's concurrency_limit."""
        job = Job(
            concurrency_key="limited_task",
            class_name="tests.dummy.tasks.limited_task",
        )
        proxy = Semaphore.Proxy(job)

        # limited_task has default limit of 1
        self.assertEqual(proxy.limit, 1)

    def test_wait_handles_existing_semaphore_at_limit(self):
        """When semaphore exists at limit=1 and value=1, wait should decrement."""
        # Pre-create semaphore at full capacity
        Semaphore.objects.create(key="limited_task", value=1)

        job = Job(
            concurrency_key="limited_task",
            class_name="tests.dummy.tasks.limited_task",
        )

        # wait() should succeed and decrement
        result = Semaphore.objects.wait(job)

        self.assertTrue(result)
        self.assertEqual(Semaphore.objects.get(key="limited_task").value, 0)
