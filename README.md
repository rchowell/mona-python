# mona

Official Python SDK for [MonaDB](https://github.com/) — a multi-tenant document
database. Sync and async, built on [httpx](https://www.python-httpx.org/) and
[pydantic](https://docs.pydantic.dev/).

> **Note:** install the PyPI distribution **`mona-preview`** while the `mona` name is
> being acquired. The import package is always `mona`. Do not install `mona-preview`
> and `mona` in the same environment.

## Install

```bash
pip install mona-preview
```

From source:

```bash
git clone https://github.com/rchowell/mona-python.git
cd mona-python
pip install -e .
```

## Usage

```python
from mona import Client

mo = Client(api_key="mk-...", base_url="https://mona.example.workers.dev")

mo.databases.create(name="beatles")

db = mo.databases["beatles"]
db.execute(
    [
        "create table beatles;",
        "insert into beatles ({ name: 'John' }, { name: 'Paul' }, { name: 'George' }, { name: 'Ringo' });",
    ]
)

rows = db.fetchall("select * from beatles;")
print(rows)
# [{"name": "John"}, {"name": "Paul"}, {"name": "George"}, {"name": "Ringo"}]
```

`databases["name"]` returns a MonaDB-style handle: `execute` runs SQL (one
statement or a batch), and `fetchall` reads rows back. Chain calls work too:

```python
rows = db.execute("select * from beatles;").fetchall()
```

Control-plane helpers (`create`, `list`, `get`, `delete`) stay on
`client.databases`. The legacy `client.databases.query(name, sql)` wrapper still
works and returns a `QueryResult`.

### Async

```python
from mona import AsyncClient

async with AsyncClient(api_key="mk-...", base_url="https://mona.example.workers.dev") as mo:
    await mo.databases.create(name="beatles")
    db = mo.databases["beatles"]
    await db.execute(["create table beatles;"])
    rows = await db.fetchall("select * from beatles;")
```

### Configuration

| Argument         | Env             | Default | Notes                                              |
| ---------------- | --------------- | ------- | -------------------------------------------------- |
| `api_key`        | `MONA_API_KEY`  | —       | Bearer token sent on every request.                |
| `base_url`       | `MONA_BASE_URL` | —       | Worker URL (serves control + data plane).          |
| `query_base_url` | —               | `base_url` | Override the data-plane host (local dev only).  |
| `timeout`        | —               | `30.0`  | Per-request timeout in seconds.                    |
| `max_retries`    | —               | `2`     | Retries on connection errors (httpx transport).    |

## Errors

All errors subclass `mona.MonaError`. API errors (`mona.APIError` and its subclasses
`AuthenticationError`, `BadRequestError`, `NotFoundError`, `ConflictError`) carry
`status_code`, `code`, and `message`.

## Development

```bash
just test              # unit tests only
just lint              # ruff
just typecheck         # mypy
just build             # wheel + sdist
```

Integration tests auto-skip when the stack is unreachable. Configure with
`MONA_CONTROL_URL` (default `http://localhost:8082`), `MONA_EDGE_URL`
(default `http://localhost:8080`), and `MONA_API_KEY` (default `dev-key`).

## Publishing

1. Bump `src/mona/_version.py`.
2. Create a GitHub release tagged `v0.1.0-preview` (triggers `.github/workflows/publish.yml`), or run `just publish` locally with `UV_PUBLISH_TOKEN` set.
3. On [PyPI](https://pypi.org/), add a trusted publisher for `mona-preview` pointing at `rchowell/mona-python` (recommended over long-lived API tokens).
