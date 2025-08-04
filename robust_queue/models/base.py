import uuid
from contextlib import contextmanager

from django.db import models, transaction

from .mixins import CreatedAtMixin


class BaseModel(CreatedAtMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

    @contextmanager
    def lock(self):
        with transaction.atomic():
            self.refresh_from_db(from_queryset=type(self).objects.select_for_update())
            yield
