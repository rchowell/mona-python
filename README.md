# mona

Official Python SDK for [MonaDB](https://monadb.com/). Sync and async, built on [httpx](https://www.python-httpx.org/) and
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

db = mo.database("beatles")
db.execute("create table beatles;")
db.insert(
    "beatles",
    {"name": "John"},
    {"name": "Paul"},
    {"name": "George"},
    {"name": "Ringo"},
)

rows = db.fetchall("select * from beatles;")
print(rows)
# [{"name": "John"}, {"name": "Paul"}, {"name": "George"}, {"name": "Ringo"}]
```

`database("name")` returns a handle for running SQL. Use `insert` for rows,
`execute` for DDL and other statements (one statement or a batch), and
`fetchall` to read rows back. Chain calls work too:

```python
rows = db.execute("select * from beatles;").fetchall()
```

Control-plane helpers (`create`, `list`, `get`, `delete`) stay on
`client.databases`.

### Async

```python
from mona import AsyncClient

async with AsyncClient(api_key="mk-...", base_url="https://mona.example.workers.dev") as mo:
    await mo.databases.create(name="beatles")
    db = mo.database("beatles")
    await db.execute("create table beatles;")
    await db.insert(
        "beatles",
        {"name": "John"},
        {"name": "Paul"},
        {"name": "George"},
        {"name": "Ringo"},
    )
    rows = await db.fetchall("select * from beatles;")
```

### Configuration

| Argument         | Env             | Default    | Notes                                           |
| ---------------- | --------------- | ---------- | ----------------------------------------------- |
| `api_key`        | `MONA_API_KEY`  | —          | Bearer token sent on every request.             |
| `base_url`       | `MONA_BASE_URL` | —          | Worker URL (serves control + data plane).       |
| `query_base_url` | —               | `base_url` | Override the data-plane host (local dev only).  |
| `timeout`        | —               | `30.0`     | Per-request timeout in seconds.                 |
| `max_retries`    | —               | `2`        | Retries on connection errors (httpx transport). |

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

## Publishing

GitHub release tags (e.g. `v0.1.0-preview`) and the PyPI version in `src/mona/_version.py`
(e.g. `0.1.0`) are set independently. Preview tags on GitHub, semver on PyPI.

1. Bump `src/mona/_version.py` (PyPI version).
2. Create a GitHub release with a preview tag (e.g. `v0.1.0-preview`), or run `just publish` locally with `UV_PUBLISH_TOKEN` set.
3. On [PyPI](https://pypi.org/), add a trusted publisher for `mona-preview` pointing at `rchowell/mona-python` (recommended over long-lived API tokens).
