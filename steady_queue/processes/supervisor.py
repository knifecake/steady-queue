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
from steady_queue.signals import (
    ProcessLifecycle,
    _process_signal_context,
    _send_process_signal,
    process_restarted,
    process_started,
    process_stopped,
)

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
        originating_pid = self.pid
        logger.info("starting supervisor with PID %(pid)d", {"pid": originating_pid})
        started = False
        error = None
        signal_context = None
        try:
            try:
                self.boot()
                started = True
                signal_context = _process_signal_context(self)
                _send_process_signal(process_started, self, context=signal_context)
                # Fork only after resetting DB state (connections + psycopg pools).
                self.reset_database_connections()
                self.start_processes()
                self.launch_maintenance_task()
            except SystemExit:
                logger.info("supervisor interrupted during boot, shutting down")
                self.restore_default_signal_handlers()
                self.shutdown()
                return
            self.supervise()
        except BaseException as exception:
            error = exception
            raise
        finally:
            if started and self.pid == originating_pid:
                _send_process_signal(
                    process_stopped, self, context=signal_context, error=error
                )

    def boot(self) -> None:
        super().boot()
        self.fail_orphaned_executions()

    def start_processes(self) -> None:
        for process in self.configuration.configured_processes:
            self.start_process(process)

    def supervise(self):
        self.is_supervising = True
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

    def start_process(self, process: Configuration.Process) -> int:
        logger.info("starting process %(process)s", {"process": process})
        instance = process.instantiate()
        instance.supervisor = self.process
        instance.mode = "fork"

        # Replacement recovery queries the database after the startup reset.
        # Clear that connection and pool state before the child inherits it.
        self.reset_database_connections()
        if (pid := os.fork()) == 0:
            # child
            instance.start()
            sys.exit(0)  # Ensure child process exits after instance.start()

        # parent
        self.reset_database_connections()
        self.configured_processes[pid] = process
        self.forks[pid] = instance
        return pid

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

            self.configured_processes.pop(pid, None)

    def replace_fork(self, pid: int, exitcode: int) -> None:
        logger.info("replacing fork %s due to exit code %s", pid, exitcode)
        if terminated_fork := self.forks.pop(pid, None):
            self.handle_claimed_jobs_by(terminated_fork, exitcode)
            replacement_pid = self.start_process(self.configured_processes.pop(pid))
            process_restarted.send(
                sender=ProcessLifecycle,
                process_kind=terminated_fork.kind,
                process_name=terminated_fork.name,
                pid=pid,
                hostname=terminated_fork.hostname,
                metadata=terminated_fork.metadata,
                exitcode=exitcode,
                replacement_pid=replacement_pid,
                supervisor_pid=self.pid,
            )

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
