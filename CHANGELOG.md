# Changelog

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
