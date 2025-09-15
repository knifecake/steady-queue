from django.db.models import QuerySet
from django.test import TestCase

from steady_queue.models.job import Job
from steady_queue.models.ready_execution import ReadyExecution
from steady_queue.queue_selector import QueueSelector


class TestQueueSelector(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.job_1 = cls.create_dummy_job_in_queue("q1")
        cls.job_2 = cls.create_dummy_job_in_queue("q2")
        cls.job_3 = cls.create_dummy_job_in_queue("q3")
        cls.job_4 = cls.create_dummy_job_in_queue("p1")
        cls.job_5 = cls.create_dummy_job_in_queue("p2")

    def test_asterisk_returns_all_queues(self):
        selector = QueueSelector(["*"], ReadyExecution.objects)
        self.assertQuerySetListEqual(
            selector.scoped_relations(),
            [ReadyExecution.objects.all()],
        )

    def test_asterisk_plus_queue_returns_all_queues(self):
        selector = QueueSelector(["*", "q2"], ReadyExecution.objects)
        self.assertQuerySetListEqual(
            selector.scoped_relations(),
            [ReadyExecution.objects.all()],
        )

    def test_queue_list_returns_only_those_queues_in_order(self):
        selector = QueueSelector(["q2", "q1"], ReadyExecution.objects)
        self.assertQuerySetListEqual(
            selector.scoped_relations(),
            [
                ReadyExecution.objects.queued_as("q2"),
                ReadyExecution.objects.queued_as("q1"),
            ],
        )

    def test_queue_prefix_returns_only_matching_queues(self):
        selector = QueueSelector(["p*"], ReadyExecution.objects)
        self.assertQuerySetListEqual(
            selector.scoped_relations(),
            [
                ReadyExecution.objects.queued_as("p1"),
                ReadyExecution.objects.queued_as("p2"),
            ],
        )

    def test_queue_name_plus_prefix_returns_only_matching_queues_in_order(self):
        selector = QueueSelector(["q1", "p*"], ReadyExecution.objects)
        self.assertQuerySetListEqual(
            selector.scoped_relations(),
            [
                ReadyExecution.objects.queued_as("q1"),
                ReadyExecution.objects.queued_as("p1"),
                ReadyExecution.objects.queued_as("p2"),
            ],
        )

    def assertQuerySetListEqual(
        self, actual_querysets: list[QuerySet], expected_querysets: list[QuerySet]
    ):
        self.assertEqual(len(actual_querysets), len(expected_querysets))
        for idx, (q, e) in enumerate(zip(actual_querysets, expected_querysets)):
            self.assertQuerySetEqual(
                q, e, ordered=False, msg=f"Querysets on index {idx} do not match"
            )

    @staticmethod
    def create_dummy_job_in_queue(queue_name: str) -> Job:
        job = Job.objects.create(
            queue_name=queue_name, class_name="test.dummy", arguments={}
        )
        return ReadyExecution.objects.create(
            job=job,
            **ReadyExecution.attributes_from_job(job),
        )
