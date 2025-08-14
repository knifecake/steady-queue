# Robust Queue

## TODOs

- [x] Enqueue jobs
- [x] Get the dispatcher to dispatch
- [x] Get the worker to work
- [x] Run after with timedelta
- [x] Errors in tasks
- [x] Manual task retries
- [x] TimerTask shutdowns
- [x] Settings
- [x] Maintenance: cleanup orphaned jobs
- [x] Maintenance: prune dead processes
- [x] Graceful worker termination
- [x] Recurring tasks
- [x] Workers per queue
- [x] Store process metadata
- [x] Primary keys
- [x] Compress migrations
- [x] Argument serialization review
- [x] Task backend capabilities
- [x] Django admin for everything -> check out mission control jobs
- [x] Queue pausing from admin
- [x] Pre-commit
- [x] CI
- [x] Pidfiles
- [x] Reorganize code
- [ ] Review logging noisiness
- [ ] Concurrency controls
- [ ] Tests
- [ ] Use postgresql
- [ ] Documentation
- [ ] Remove demo app in favor of test dummy
- [ ] Class-based tasks
- [ ] Django checks
- [ ] Retry on database is locked
- [ ] Django admin permissions
- [ ] Signals: pre/post enqueue, pre/post perform
- [ ] Contributing
- [ ] Readme

## Deviations from solid queue

- Job doesn't work with classes, only with objects
- No support for setting the procline
- Callbacks
