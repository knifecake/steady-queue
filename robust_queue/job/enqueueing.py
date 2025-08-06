from robust_queue.job.errors import EnqueueError


class Enqueueing:
    @classmethod
    def perform_all_later(jobs):
        raise NotImplementedError

    enqueue_after_transaction_commits: bool = False

    def enqueue(self, **kwargs):
        self.set(**kwargs)
        self.successfully_enqueued = False

        self.raw_enqueue()

        if self.successfully_enqueued:
            return self

        return False

    def raw_enqueue(self):
        try:
            if self.scheduled_at:
                raise NotImplementedError
            else:
                raise NotImplementedError

            self.successfully_enqueued = True
        except EnqueueError as e:
            self.enqueue_error = e
