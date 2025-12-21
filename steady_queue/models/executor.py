class Executor:
    def fail_all_claimed_executions_with(self, error: str):
        if not self.is_claiming_executions:
            return

        self.claimed_executions.fail_all_with(error)

    def release_all_claimed_executions(self):
        if not self.is_claiming_executions:
            return

        self.claimed_executions.release_all()

    @property
    def is_claiming_executions(self):
        return self.kind == "worker"
