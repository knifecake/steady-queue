from robust_queue.task import BaseTask


class FooTask(BaseTask):
    def perform(self, foo: int):
        return foo * 2
