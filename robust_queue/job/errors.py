class UnknownJobClassError(Exception):
    def __init__(self, job_class_name: str):
        self.job_class_name = job_class_name

    def __str__(self):
        return f"Unknown job class: {self.job_class_name}"


class EnqueueError(Exception):
    pass
