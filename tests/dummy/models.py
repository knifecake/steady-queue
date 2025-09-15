from django.db import models

from .tasks import dummy_task


class Dummy(models.Model):
    name = models.CharField(max_length=100)

    def work(self):
        dummy_task.enqueue()
