from django.test import TestCase

from steady_queue.models import Job
from tests.dummy.tasks import limited_task


class ConcurrencyControlsTestCase(TestCase):
    def test_enqueueing_limited_tasks_are_blocked(self):
        task1 = limited_task.enqueue()
        task2 = limited_task.enqueue()

        self.assertEqual(Job.objects.get(id=task1.id).status, "ready")
        self.assertEqual(Job.objects.get(id=task2.id).status, "blocked")
