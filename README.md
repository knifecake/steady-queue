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
- [ ] Workers per queue
- [ ] Review logging noisiness
- [ ] Use postgresql
- [ ] Reorganize code
- [ ] Concurrency controls
- [ ] Tests
- [ ] Documentation
- [ ] CI
- [ ] Retry on database is locked
- [ ] Django admin for everything -> check out mission control jobs
- [ ] Django admin permissions
- [ ] Signals: pre/post enqueue, pre/post perform

## Deviations from solid queue

- Job doesn't work with classes, only with objects
- No support for setting the procline
- Callbacks