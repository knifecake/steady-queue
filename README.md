# Robust Queue

## TODOs

- [ ] Enqueue jobs
- [ ] Get the dispatcher to dispatch
- [ ] Get the worker to work
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