class Execution:
    @classmethod
    def class_perform_now(cls, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def execute(cls, job_data):
        job = cls.deserialize(job_data)
        job.perform_now()

    def perform_now(self):
        try:
            # TODO: do we need this?
            self.executions = (self.executions or 0) + 1

            self._deserialize_arguments_if_needed()

            self.perform()
        except Exception as e:
            # TODO: handling
            raise e

    def perform(**kwargs):
        raise NotImplementedError
