from django.tasks import task
from django.test import SimpleTestCase

from steady_queue.recurring_task import configurations, recurring


@recurring(schedule="*/1 * * * *", key="test_recurring_task")
@task()
def test_recurring_task():
    pass


class RecurringDecoratorTestCase(SimpleTestCase):
    def test_decorator_registers_recurring_task(self):
        self.assertIn("test_recurring_task", [c.key for c in configurations])
