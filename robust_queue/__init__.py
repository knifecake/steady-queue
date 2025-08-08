from datetime import timedelta

process_heartbeat_interval: timedelta = timedelta(minutes=1)

process_alive_threshold: timedelta = timedelta(minutes=5)

shutdown_timeout: timedelta = timedelta(seconds=5)

preserve_finished_jobs: bool = True

clear_finished_jobs_after: timedelta = timedelta(days=1)

default_concurrency_control_period: timedelta = timedelta(minutes=3)
