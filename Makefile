test:
	uv run python runtests.py

test.postgres:
	tests/bin/run-docker-postgres
	DB_URL=postgres://steady_queue:steady_queue@localhost:5432/steady_queue uv run python runtests.py

lint:
	uv run pre-commit run --all-files
