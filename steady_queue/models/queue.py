from django.db import models

from steady_queue.models.pause import Pause
from steady_queue.models.ready_execution import ReadyExecution


class QueueQuerySet(models.QuerySet):
    def pause(self) -> int:
        count = self.count()
        for queue in self:
            queue.pause()
        return count

    def resume(self) -> int:
        count = self.count()
        for queue in self:
            queue.resume()
        return count


class QueueManager(models.Manager):
    def get_queryset(self):
        return QueueQuerySet(self.model, using=self._db).only("queue_name").distinct()


class Queue(models.Model):
    # A fake model to be able to display a queues admin in the Django admin site.
    class Meta:
        managed = False
        db_table = "steady_queue_job"

    objects = QueueManager()

    queue_name = models.CharField(
        max_length=255, db_column="queue_name", primary_key=True
    )

    @property
    def pending_jobs(self) -> int:
        return ReadyExecution.objects.queued_as(self.queue_name).count()

    @property
    def is_paused(self) -> bool:
        return Pause.objects.filter(queue_name=self.queue_name).exists()

    @property
    def is_running(self) -> bool:
        return not self.is_paused

    def pause(self) -> None:
        Pause.objects.get_or_create(queue_name=self.queue_name)

    def resume(self) -> None:
        Pause.objects.filter(queue_name=self.queue_name).delete()

    def __str__(self) -> str:
        return self.queue_name
