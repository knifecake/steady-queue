# Changelog

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
