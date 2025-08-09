from django.test import SimpleTestCase, TestCase

from robust_queue.arguments import Arguments
from tests.dummy.models import Dummy


class TestArguments(SimpleTestCase):
    def test_primitive_type_serialization(self):
        subjects = [1, 1.0, "a", "abc", True, False, None]
        for subject in subjects:
            self.assertEqual(
                [subject], Arguments.deserialize(Arguments.serialize([subject]))
            )

    def test_list_serialization(self):
        subjects = [[1, 2, 3], [1.0, 2.0, 3.0], ["a", "b", "c"], [True, False], [None]]
        for subject in subjects:
            self.assertEqual(
                [subject], Arguments.deserialize(Arguments.serialize([subject]))
            )

    def test_dict_serialization(self):
        subjects = [
            {"a": 1, "b": 2, "c": 3},
            {"a": [1, 2, 3], "b": [4, 5, 6]},
        ]
        for subject in subjects:
            self.assertEqual(
                [subject], Arguments.deserialize(Arguments.serialize([subject]))
            )


class TestModelSerialization(TestCase):
    def test_model_serialization(self):
        saved_instance = Dummy.objects.create(name="test")

        self.assertEqual(
            [saved_instance],
            Arguments.deserialize(Arguments.serialize([saved_instance])),
        )
