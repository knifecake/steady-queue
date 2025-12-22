# Contributing to Steady Queue

## Running the test suite

```bash
make test
```

## Running the test dummy project

In addition to acting as a dummy for tests, `tests.dummy` is a Django project you can interact with via the admin interface or the shell:

```bash
# Run the webserver
uv run python manage.py runserver

# Run a shell
uv run python manage.py shell

# Run the steady queue supervisor
uv run python manage.py steady_queue
```
