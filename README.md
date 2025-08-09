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
- [ ] Primary keys
- [ ] Class-based tasks
- [ ] Argument serialization review
- [x] Task backend capabilities
- [ ] Review logging noisiness
- [ ] Pidfiles
- [x] Reorganize code
- [ ] Concurrency controls
- [ ] Tests
- [ ] Use postgresql
- [ ] Documentation
- [ ] CI
- [x] Pre-commit
- [ ] Queue pausing from admin
- [ ] Django checks
- [ ] Retry on database is locked
- [ ] Django admin for everything -> check out mission control jobs
- [ ] Django admin permissions
- [ ] Signals: pre/post enqueue, pre/post perform

## Deviations from solid queue

- Job doesn't work with classes, only with objects
- No support for setting the procline
- Callbacks
