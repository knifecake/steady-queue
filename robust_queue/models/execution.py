from .base import BaseModel


class Execution(BaseModel):
    class Meta:
        abstract = True

    @property
    def type(self):
        raise NotImplementedError
