class QueueName:
    default_queue_name: str = "default"
    queue_name: str

    def get_queue_name(self) -> str:
        return self.queue_name or self.default_queue_name
