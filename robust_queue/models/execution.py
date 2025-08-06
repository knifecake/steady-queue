from django.db import models

from .base import BaseModel


class ExecutionQuerySet(models.QuerySet):
    def ordered(self):
        return self.order_by("priority", "job_id")


class Execution(BaseModel):
    class Meta:
        abstract = True

    @property
    def type(self):
        raise NotImplementedError
