import time
from datetime import datetime, timedelta
from typing import Optional

from django.db import models
from django.utils import timezone

import steady_queue


class ClearableQuerySet(models.QuerySet):
    def clearable(
        self,
        finished_before: Optional[datetime] = None,
        class_name: Optional[str] = None,
    ):
        if finished_before is None:
            finished_before = timezone.now() - steady_queue.clear_finished_jobs_after

        queryset = self.exclude(finished_at__isnull=True).filter(
            finished_at__lt=finished_before
        )

        if class_name is not None:
            queryset = queryset.filter(class_name=class_name)

        return queryset

    def clear_finished_in_batches(
        self,
        batch_size: int = 500,
        finished_before: Optional[datetime] = None,
        class_name: Optional[str] = None,
        sleep_between_batches: Optional[timedelta] = None,
    ):
        if sleep_between_batches is None:
            sleep_between_batches = timedelta(seconds=0)

        while True:
            ids = list(
                self.clearable(finished_before, class_name)[:batch_size].values_list(
                    "pk", flat=True
                )
            )
            deleted, _ = self.filter(pk__in=ids).delete()
            if deleted == 0:
                break

            time.sleep(sleep_between_batches.total_seconds())
