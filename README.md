# Robust Queue

## TODOs

- [x] Enqueue jobs
- [x] Get the dispatcher to dispatch
- [x] Get the worker to work
- [ ] Maintenance
- [ ] Workers per queue
- [ ] Use postgresql
- [ ] Reorganize code
- [ ] Recurring tasks
- [ ] Concurrency controls
- [ ] Django admin for everything -> check out mission control jobs
- [ ] Django admin permissions

## Deviations from solid queue

- Job doesn't work with classes, only with objects
- No support for setting the procline
- Callbacks