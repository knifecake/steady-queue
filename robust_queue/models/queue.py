from django.db import models

from robust_queue.models.pause import Pause
from robust_queue.models.ready_execution import ReadyExecution


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
        db_table = "robust_queue_job"

    objects = QueueManager()

    queue_name = models.CharField(
        max_length=255, db_column="queue_name", primary_key=True
    )

    @property
    def pending_jobs(self):
        return ReadyExecution.objects.queued_as(self.queue_name).count()

    @property
    def is_paused(self):
        return Pause.objects.filter(queue_name=self.queue_name).exists()

    @property
    def is_running(self):
        return not self.is_paused

    def pause(self):
        Pause.objects.get_or_create(queue_name=self.queue_name)

    def resume(self):
        Pause.objects.filter(queue_name=self.queue_name).delete()

    def __str__(self):
        return self.queue_name
