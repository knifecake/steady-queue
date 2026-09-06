from django.dispatch import Signal


class ProcessLifecycle:
    """Public sender for process lifecycle signals."""


class QueueLifecycle:
    """Public sender for queue lifecycle signals."""


# Process lifecycle signals carry stable data suitable for logs and metrics.
process_started = Signal()
process_stopped = Signal()
process_restarted = Signal()

# Queue control signals. Receivers get ``queue_name`` and ``changed``.
queue_paused = Signal()
queue_resumed = Signal()


def _process_signal_context(process) -> dict:
    return {
        "process_kind": process.kind,
        "process_name": process.name,
        "pid": process.pid,
        "hostname": process.hostname,
        "metadata": process.metadata,
    }


def _send_process_signal(signal: Signal, process, *, context=None, **kwargs) -> None:
    signal.send(
        sender=ProcessLifecycle,
        **(context or _process_signal_context(process)),
        **kwargs,
    )
