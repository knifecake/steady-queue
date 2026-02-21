.PHONY: test
test:
	tests/bin/run-docker-postgres
	uv run python runtests.py

.PHONY: steady_queue
steady_queue:
	tests/bin/run-docker-postgres
	uv run python manage.py steady_queue

.PHONY: lint
lint:
	uv run ruff check --fix
	uv run ruff format

.PHONY: docs
docs:
	uv run --group docs -m sphinx -b html docs docs/_build/html

.PHONY: force-kill
force-kill:
	ps | grep steady_queue | cut -f 1  -d ' '  | xargs kill -9
	rm -f tmp/pids/steady_queue_supervisor.pid
