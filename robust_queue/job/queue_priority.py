class QueuePriority:
    default_priority: int = 0
    priority: int

    def get_priority(self) -> int:
        return self.priority or self.default_priority
