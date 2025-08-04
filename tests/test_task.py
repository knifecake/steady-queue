from django.test import TestCase

from robust_queue.models.job import Job
from tests.dummy.tasks import FooTask


class TestTask(TestCase):
    def test_perform(self):
        self.assertEqual(FooTask.perform_now(foo=2), 4)

    def test_perform_later(self):
        FooTask.perform_later(foo=2)

        self.assertEqual(Job.objects.count(), 1)
        job = Job.objects.first()
        self.assertEqual(job.queue_name, "default")
        self.assertEqual(job.class_name, "tests.dummy.tasks.FooTask")
        self.assertEqual(job.arguments, {"foo": 2})
        self.assertEqual(job.priority, 0)
        self.assertIsNone(job.scheduled_at)
        self.assertIsNotNone(job.django_task_id)
