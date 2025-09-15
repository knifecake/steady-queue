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
	uv run pre-commit run --all-files
