from django.test import TestCase
from django.utils import timezone

from steady_queue.configuration import Configuration
from steady_queue.models import Job, RecurringExecution, RecurringTask
from tests.dummy.tasks import dummy_task


class RecurringExecutionTestCase(TestCase):
    def test_enqueue_same_run_at_only_enqueues_once(self):
        recurring_task = RecurringTask.from_configuration(
            Configuration.RecurringTask(
                key="test-recurring-task",
                class_name="tests.dummy.tasks.dummy_task",
                schedule="* * * * *",
                arguments=dummy_task.serialize([], {}),
                queue_name="default",
                priority=0,
            )
        )
        recurring_task.save()

        run_at = timezone.now().replace(second=0, microsecond=0)

        first_result = recurring_task.enqueue(run_at=run_at)
        second_result = recurring_task.enqueue(run_at=run_at)

        self.assertNotEqual(first_result, False)
        self.assertFalse(second_result)

        self.assertEqual(Job.objects.count(), 1)
        self.assertEqual(RecurringExecution.objects.count(), 1)

        recurring_execution = RecurringExecution.objects.get()
        self.assertEqual(recurring_execution.task_id, recurring_task.key)
        self.assertEqual(recurring_execution.run_at, run_at)
