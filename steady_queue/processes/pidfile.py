import os


class Pidfile:
    def __init__(self, path: str):
        self.path = path
        self.pid = os.getpid()

    def setup(self):
        self.check_status()
        self.write_file()

    def delete(self):
        self.delete_file()

    def check_status(self):
        try:
            with open(self.path, "r") as f:
                existing_pid = int(f.read().strip())
                if existing_pid > 0:
                    os.kill(existing_pid, 0)

                self.already_running()
        except FileNotFoundError:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        except ProcessLookupError:
            self.delete()
        except PermissionError:
            self.already_running()

    def write_file(self):
        try:
            with open(self.path, mode="xt") as f:
                f.write(str(self.pid))
        except FileExistsError:
            self.check_status()
            self.write_file()

    def delete_file(self):
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def already_running(self):
        raise RuntimeError(
            f"A Steady Queue supervisor is already running. Check {self.path}"
        )
