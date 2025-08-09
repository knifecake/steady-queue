from functools import reduce
from operator import or_

from django.db.models import QuerySet

from robust_queue.collections import compact, flat_map
from robust_queue.models.pause import Pause


class QueueSelector:
    raw_queues: list[str]
    queryset: QuerySet

    def __init__(self, queue_list: list[str], queryset: QuerySet):
        self.raw_queues = queue_list
        self.queryset = queryset

    def scoped_relations(self) -> list[QuerySet]:
        if self.is_all:
            return [self.queryset.all()]
        elif self.is_none:
            return [self.queryset.none()]
        else:
            return [
                self.queryset.queued_as(queue_name) for queue_name in self.queue_names
            ]

    @property
    def is_all(self) -> bool:
        return self.include_all_queues and len(self.paused_queues) == 0

    @property
    def is_none(self) -> bool:
        return len(self.queue_names) == 0

    @property
    def queue_names(self) -> list[str]:
        return list(set(self.eligible_queues) - set(self.paused_queues))

    @property
    def eligible_queues(self) -> list[str]:
        if self.include_all_queues:
            return self.all_queues
        else:
            return self.in_raw_order(self.exact_names + self.prefixed_names)

    @property
    def include_all_queues(self) -> bool:
        return "*" in self.raw_queues

    @property
    def all_queues(self) -> list[str]:
        return self.queryset.values_list("queue_name", flat=True).distinct()

    @property
    def exact_names(self) -> list[str]:
        return [q for q in self.raw_queues if self.is_exact_name(q)]

    @property
    def prefixed_names(self) -> list[str]:
        if len(self.prefixes) == 0:
            return []
        else:
            return (
                reduce(
                    or_,
                    [
                        self.queryset.filter(queue_name__startswith=p)
                        for p in self.prefixes
                    ],
                )
                .values_list("queue_name", flat=True)
                .distinct()
            )

    @property
    def prefixes(self) -> list[str]:
        return [q.replace("*", "") for q in self.raw_queues if self.is_prefixed_name(q)]

    def is_exact_name(self, name: str) -> bool:
        return "*" not in name

    def is_prefixed_name(self, name: str) -> bool:
        return name.endswith("*")

    @property
    def paused_queues(self) -> list[str]:
        return Pause.objects.values_list("queue_name", flat=True)

    def in_raw_order(self, queues: list[str]) -> list[str]:
        if len(queues) == 1 or len(self.prefixes) == 0:
            return queues

        queues = queues.copy()
        return list(
            compact(
                flat_map(
                    lambda raw_queue: self.delete_in_order(raw_queue, queues),
                    self.raw_queues,
                )
            )
        )

    def delete_in_order(self, raw_queue: str, queues: list[str]) -> list[str]:
        if self.is_exact_name(raw_queue):
            return queues.remove(raw_queue)
        elif self.is_prefixed_name(raw_queue):
            prefix = raw_queue.replace("*", "")
            matches = [q for q in queues if q.startswith(prefix)]
            queues -= matches
            return queues
