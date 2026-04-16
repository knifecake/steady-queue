# Changelog

## Unreleased

**Fixed:**

- Fixed supervisor child-process crash loops (`exit code 11`) seen with
  Django/PostgreSQL pooling by resetting DB state before forking and clearing
  Django's class-level psycopg pool cache in the forking path (#48).
- Keep database pooling enabled while resetting fork-inherited connection state
  so child processes can establish fresh pools after forking.
- Validate worker thread sizing against PostgreSQL `OPTIONS.pool.max_size`
  (when explicitly configured), mirroring Solid Queue's pool sizing check.

## v0.1.8 - 2026-03-08

**Fixed:**

- Default `steady_queue.supervisor_pidfile` is now `None` (disabled by
  default), matching Solid Queue and avoiding stale pidfile issues in
  containerized deployments.
- Supervisor pidfiles now register an `atexit` cleanup hook so graceful exits
  remove the pidfile more reliably.

## v0.1.7 - 2026-02-21

**Added:**

- Sphinx documentation site covering installation, getting started,
  configuration, API reference, internals and alternatives (#13). Published
  to Read The Docs.

**Fixed:**

- Fixed a bug where the process would hang on shutdown and require `kill -9`.
  Timer threads (heartbeat, maintenance) are now daemon threads, matching
  Ruby's default thread behaviour (#16).
- Fixed `skip_recurring` not actually skipping scheduling and execution of
  recurring tasks — it now excludes the scheduler process entirely (#37).

## v0.1.6 - 2026-02-17

**Fixed:**

- Bump package version not included in previous release.

## v0.1.5 - 2026-02-17

**Added:**

- Explicit support for Python 3.14

**Fixed:**

- Fixed a bug where the supervisor wouldn't respond to SIGINT while booting if
  Django was waiting on the database connection pool (#16).
- Fixed serialization of `datetime`, `date`, `time`, and `timedelta` objects
  passed as task arguments (#30).
- Fixed some race conditions during process supervision and heartbeats (#29).
- Fixed double claiming for concurrency-limited tasks (#28).

## v0.1.4 - 2026-02-06

**Fixed:**

- Fixes a bug where enqueueing tasks that would be blocked failed due to status
  not being able to be reported (#18).

## v0.1.3 - 2026-02-05

**Fixed:**

- Properly handle callable keys for concurrency-controlled tasks (#14).
- More explicitly clarify the limitations of the backend, namely no support for
  result fetching or async enqueueing (#12).

## v0.1.2 - 2025-12-29

**Fixed:**

- Fixed an error that prevented calling
  `Job.objects.clear_finished_in_batches()` to periodically clean up the
  database per the documentation.

## v0.1.1 - 2025-12-22

**Fixed:**

- Fix error when pruning processes due to missing transaction wrapper.

## v0.1.0 - 2025-12-22

Initial release.
