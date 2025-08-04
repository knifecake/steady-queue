import time

from django.db import models
from django.utils import timezone


class ClearableQuerySet(models.QuerySet):
    def clearable(
        self, finished_before: timezone.datetime = None, class_name: str = None
    ):
        if finished_before is None:
            finished_before = timezone.now() - timezone.timedelta(
                days=30
            )  # TODO: configurable

        queryset = self.exclude(finished_at__isnull=True).filter(
            finished_at__lt=finished_before
        )

        if class_name is not None:
            queryset = queryset.filter(class_name=class_name)

        return queryset

    def clear_finished_in_batches(
        self,
        batch_size: int = 500,
        finished_before: timezone.datetime = None,
        class_name: str = None,
        sleep_between_batches: timezone.timedelta = None,
    ):
        if sleep_between_batches is None:
            sleep_between_batches = timezone.timedelta(seconds=0)

        while True:
            deleted = self.clearable(finished_before, class_name)[:batch_size].delete()
            if deleted == 0:
                break

            time.sleep(sleep_between_batches.total_seconds())
