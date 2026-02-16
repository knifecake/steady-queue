from datetime import date, datetime, time, timedelta, timezone

from django.test import SimpleTestCase, TestCase
from django.utils import timezone as dj_tz

from steady_queue.arguments import Arguments
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

    def test_datetime_serialization(self):
        subjects = [
            datetime(2026, 2, 12, 11, 21, 9, 976000),
            date(2026, 2, 12),
            time(11, 21, 9, 976000),
        ]
        for subject in subjects:
            self.assertEqual(
                [subject], Arguments.deserialize(Arguments.serialize([subject]))
            )

    def test_datetime_as_kwarg(self):
        args = (1,)
        kwargs = {"send_after": datetime(2026, 2, 12, 11, 21, 9)}
        serialized = Arguments.serialize_args_and_kwargs(args, kwargs)
        deserialized_args, deserialized_kwargs = Arguments.deserialize_args_and_kwargs(
            serialized
        )
        self.assertEqual(list(args), deserialized_args)
        self.assertEqual(kwargs, deserialized_kwargs)

    def test_datetime_in_list(self):
        subject = [datetime(2026, 1, 1), datetime(2026, 6, 15)]
        self.assertEqual(
            [subject], Arguments.deserialize(Arguments.serialize([subject]))
        )

    def test_datetime_in_dict(self):
        subject = {"start": datetime(2026, 1, 1), "end": datetime(2026, 12, 31)}
        self.assertEqual(
            [subject], Arguments.deserialize(Arguments.serialize([subject]))
        )

    def test_timezone_aware_datetime_serialization(self):
        subjects = [
            dj_tz.now(),
            datetime(2026, 2, 12, 11, 21, 9, tzinfo=timezone.utc),
            datetime(2026, 6, 15, 8, 0, 0, tzinfo=timezone(timedelta(hours=2))),
        ]
        for subject in subjects:
            self.assertEqual(
                [subject], Arguments.deserialize(Arguments.serialize([subject]))
            )

    def test_timedelta_serialization(self):
        subjects = [
            timedelta(days=1),
            timedelta(hours=2, minutes=30),
            timedelta(seconds=0),
            timedelta(days=7, hours=3, minutes=15, seconds=30, microseconds=500000),
            timedelta(days=-1, seconds=3600),
        ]
        for subject in subjects:
            self.assertEqual(
                [subject], Arguments.deserialize(Arguments.serialize([subject]))
            )

    def test_timedelta_as_kwarg(self):
        args = ()
        kwargs = {"delay": timedelta(minutes=5)}
        serialized = Arguments.serialize_args_and_kwargs(args, kwargs)
        _, deserialized_kwargs = Arguments.deserialize_args_and_kwargs(serialized)
        self.assertEqual(kwargs, deserialized_kwargs)


class TestModelSerialization(TestCase):
    def test_model_serialization(self):
        saved_instance = Dummy.objects.create(name="test")

        self.assertEqual(
            [saved_instance],
            Arguments.deserialize(Arguments.serialize([saved_instance])),
        )
