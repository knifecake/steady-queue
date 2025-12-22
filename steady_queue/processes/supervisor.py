import logging
import os
import signal
import sys
from datetime import timedelta
from typing import Optional

import steady_queue
from steady_queue.configuration import Configuration
from steady_queue.models.process import Process
from steady_queue.processes.base import Base
from steady_queue.processes.interruptible import Interruptible
from steady_queue.processes.maintenance import Maintenance
from steady_queue.processes.pidfiled import Pidfiled
from steady_queue.processes.registrable import Registrable
from steady_queue.processes.signals import Signals
from steady_queue.processes.timer import wait_until

logger = logging.getLogger("steady_queue")


class Supervisor(Maintenance, Signals, Pidfiled, Registrable, Interruptible, Base):
    @classmethod
    def launch(cls, options: Optional[Configuration.Options] = None) -> None:
        configuration = Configuration(options)
        if not configuration.is_valid:
            logger.error(
                "Invalid Steady Queue configuration: %(errors)s",
                {"errors": "\n".join([e.message for e in configuration.errors])},
            )
            sys.exit(1)

        return cls(configuration).start()

    def __init__(self, configuration: Configuration):
        self.configuration = configuration
        self.forks: dict[int, Base] = {}
        self.configured_processes: dict[int, Configuration.Process] = {}

        super().__init__()

    def start(self) -> None:
        logger.info("starting supervisor with PID %(pid)d", {"pid": self.pid})
        self.boot()
        self.start_processes()
        self.launch_maintenance_task()
        self.supervise()

    def boot(self) -> None:
        super().boot()
        self.fail_orphaned_executions()

    def start_processes(self) -> None:
        for process in self.configuration.configured_processes:
            self.start_process(process)

    def supervise(self):
        try:
            while True:
                if self.is_stopped:
                    logger.debug("%s breaking because is_stopped", self.name)
                    break

                self.set_procline()
                self.process_signal_queue()

                if not self.is_stopped:
                    self.reap_and_replace_terminated_forks()
                    self.interruptible_sleep(timedelta(seconds=1))
        finally:
            logger.debug("supervisor finally block")
            self.shutdown()

    def start_process(self, process: Configuration.Process) -> None:
        logger.info("starting process %(process)s", {"process": process})
        instance = process.instantiate()
        instance.supervisor = self.process
        instance.mode = "fork"

        if (pid := os.fork()) == 0:
            # child
            instance.start()
            sys.exit(0)  # Ensure child process exits after instance.start()

        # parent
        self.reset_database_connections()
        self.configured_processes[pid] = process
        self.forks[pid] = instance

    def set_procline(self) -> None:
        pass

    def terminate_gracefully(self) -> None:
        logger.info("terminating gracefully")
        self.term_forks()

        for _ in wait_until(
            steady_queue.shutdown_timeout, lambda: self.are_all_forks_terminated
        ):
            self.reap_terminated_forks()

        if not self.are_all_forks_terminated:
            logger.warning("shutdown timeout exceeded")
            self.terminate_immediately()

    def terminate_immediately(self) -> None:
        logger.warning("terminating immediately")
        self.quit_forks()

    def shutdown(self) -> None:
        self.stop_maintenance_task()
        super().shutdown()
        logger.debug("supervisor shutdown done")

    def term_forks(self) -> None:
        self.signal_processes(self.forks.keys(), signal.SIGTERM)

    def quit_forks(self) -> None:
        self.signal_processes(self.forks.keys(), signal.SIGQUIT)

    def reap_and_replace_terminated_forks(self) -> None:
        while True:
            try:
                pid, exitcode = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break
            else:
                if not pid:
                    break

            self.replace_fork(pid, exitcode)

    def reap_terminated_forks(self) -> None:
        while True:
            try:
                pid, wait_status = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break

            if not pid:
                break

            terminated_fork = self.forks.pop(pid, None)
            is_exited = os.WIFEXITED(wait_status)
            exit_status = os.WEXITSTATUS(wait_status)

            if terminated_fork and (not is_exited or exit_status > 0):
                self.handle_claimed_jobs_by(terminated_fork, wait_status)

            self.configured_processes.pop(pid)

    def replace_fork(self, pid: int, exitcode: int) -> None:
        logger.info("replacing fork %s due to exit code %s", pid, exitcode)
        if terminated_fork := self.forks.pop(pid, None):
            self.handle_claimed_jobs_by(terminated_fork, exitcode)
            self.start_process(self.configured_processes.pop(pid))

    def handle_claimed_jobs_by(self, terminated_fork: Base, exitcode: int) -> None:
        if not self.process:
            return

        registered_process: Optional[Process] = self.process.supervisees.filter(
            name=terminated_fork.name
        ).first()
        if registered_process:
            error = str(exitcode)  # parse exit code
            registered_process.fail_all_claimed_executions_with(error)

    @property
    def are_all_forks_terminated(self) -> bool:
        return len(self.forks) == 0
