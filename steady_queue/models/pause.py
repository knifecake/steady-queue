from django.db import models

from .base import BaseModel


class Pause(BaseModel):
    class Meta:
        verbose_name = "pause"
        verbose_name_plural = "pauses"
        constraints = (
            models.UniqueConstraint(
                fields=("queue_name",),
                name="uq_sq_pause_queue_name",
            ),
        )

    queue_name = models.CharField(max_length=255, verbose_name="queue name")
