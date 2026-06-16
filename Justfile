test:
    uv run pytest -m "not integration"

lint:
    uv run ruff check .
    uv run ruff format --check .

format:
    uv run ruff check --fix .
    uv run ruff format .

typecheck:
    uv run mypy src

build:
    uv build

check: lint typecheck test

# Release gate: lint + unit tests (typecheck is tracked separately via `just typecheck`).
release-check: lint test

# Dry-run against TestPyPI: requires a TestPyPI API token in UV_PUBLISH_TOKEN.
publish-test: release-check build
    uv publish --publish-url https://test.pypi.org/legacy/

# Publish to PyPI: set UV_PUBLISH_TOKEN or configure trusted publishing on GitHub.
publish: release-check build
    uv publish
