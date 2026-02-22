# SQLite → PostgreSQL Migration Guide

> **Scope:** `workshop/00_personal_todo` — FastAPI + SQLAlchemy + Alembic project  
> **Goal:** Swap out the local SQLite file for a Dockerised PostgreSQL instance with zero data loss risk and a clean migration replay.

---

## 0. Pre-flight Checklist

Before touching anything, confirm this state:

| Check | Command | Expected |
|---|---|---|
| App is **not** running | `ps aux \| grep uvicorn` | no matching process |
| Docker daemon is running | `docker info` | no error |
| You are in the project root | `pwd` | `…/db_workshop` |

> Your existing `database.db` (SQLite) is **not deleted** at any point. It stays on disk as a historical artifact.

---

## 1. Start PostgreSQL via Docker Compose

Each project has its own `docker-compose.yml` — no global containers, no port conflicts between projects.

**`workshop/00_personal_todo/docker-compose.yml`:**
```yaml
services:
  postgres:
    image: postgres:16
    container_name: personal_todo_postgres
    environment:
      POSTGRES_USER: todo_user
      POSTGRES_PASSWORD: todo_pass
      POSTGRES_DB: todo_db
    ports:
      - "5432:5432"
    volumes:
      - ../../localdev/data/personal_todo_pgdata:/var/lib/postgresql/data
```

**Key design decisions:**

| Decision | Reason |
|---|---|
| `container_name` scoped per project | Multiple projects can coexist without name clashes |
| Bind mount to `localdev/data/` | Data lives in the repo tree, visible and inspectable; not hidden in Docker internals |
| Relative path in `volumes` | Portable across machines — Docker Compose resolves relative to the compose file location |
| `postgres:16` pinned | Reproducible; avoids surprise upgrades |

**Pre-create the data directory** (bind mounts require the host path to exist first):
```bash
mkdir -p localdev/data/personal_todo_pgdata
```

**Start the database:**
```bash
make db-start
# equivalent to: docker compose up -d
```

**Verify it booted correctly:**
```bash
# Container should show STATUS = Up
docker ps | grep personal_todo_postgres

# Connect and list databases (should show todo_db)
docker exec -it personal_todo_postgres psql -U todo_user -d todo_db -c '\l'
```

> Data persists in `localdev/data/personal_todo_pgdata/` across `db-stop` / `db-start`. It is only wiped if you delete that folder manually or run `docker compose down -v`.

---

## 2. Install the PostgreSQL Python Driver

SQLAlchemy needs a DBAPI driver to talk to Postgres. `psycopg2-binary` bundles the C library so you don't need system packages.

```bash
# Run from workspace root (where pyproject.toml lives)
uv add psycopg2-binary
```

Confirm it installed:

```bash
uv run python -c "import psycopg2; print(psycopg2.__version__)"
```

> **Why `psycopg2-binary` and not `psycopg2`?**  
> The `-binary` variant includes pre-compiled C extensions. `psycopg2` (bare) requires `libpq-dev` + a C compiler — unnecessary friction for local dev.

---

## 3. Switch the Database URL — Via `.env`

Create a `.env` file **inside** `workshop/00_personal_todo/` (same directory as `main.py` and `alembic.ini`):

```bash
# workshop/00_personal_todo/.env
DATABASE_URL=postgresql+psycopg2://todo_user:todo_pass@localhost:5432/todo_db
```

`pydantic-settings` (`BaseSettings`) automatically reads `.env` files and the env value **overrides** the default in `config.py`. No source code changes needed for the URL itself.

**URL anatomy:**

```
postgresql+psycopg2 :// todo_user : todo_pass @ localhost : 5432 / todo_db
└─ dialect+driver ─┘   └─ user ──┘  └─ pass ─┘  └─ host ─┘  └─ port ─┘ └─ db ─┘
```

> **Do not commit `.env` to git.** Add it to `.gitignore` if not already present.

---

## 4. Remove the SQLite-Only Engine Argument

Open `workshop/00_personal_todo/app/core/database.py`.

`connect_args={"check_same_thread": False}` is a **SQLite-only workaround** — SQLite's threading model requires it, but Postgres does not accept it and will raise a `TypeError` at startup.

**Before:**
```python
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,
)
```

**After:**
```python
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)
```

---

## 5. Remove `render_as_batch` from Alembic's `env.py`

Open `workshop/00_personal_todo/alembic/env.py`.

`render_as_batch=True` is another **SQLite workaround**. SQLite cannot run `ALTER TABLE` statements directly, so Alembic uses a "batch" strategy (create temp table → copy → drop → rename). PostgreSQL supports full DDL — keeping this flag on is harmless but produces messier migration SQL.

Remove it from **both** functions:

**`run_migrations_offline()`** — Before:
```python
context.configure(
    url=url,
    target_metadata=target_metadata,
    render_as_batch=True,        # ← remove
    literal_binds=True,
    dialect_opts={"paramstyle": "named"},
    process_revision_directives=process_revision_directives,
)
```

**`run_migrations_offline()`** — After:
```python
context.configure(
    url=url,
    target_metadata=target_metadata,
    literal_binds=True,
    dialect_opts={"paramstyle": "named"},
    process_revision_directives=process_revision_directives,
)
```

**`run_migrations_online()`** — Before:
```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    render_as_batch=True,        # ← remove
    process_revision_directives=process_revision_directives,
)
```

**`run_migrations_online()`** — After:
```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    process_revision_directives=process_revision_directives,
)
```

> **What about existing migration files that use `op.batch_alter_table`?**  
> The four `2026_02_21_*` files already written use `batch_alter_table` — that's fine. It still runs correctly on Postgres; it just issues standard `ALTER TABLE` under the hood. You don't need to rewrite them.

---

## 6. Run All Migrations on the Fresh Postgres DB

The new Postgres database is completely empty — no tables, no `alembic_version` tracking table. Replay all migrations from the beginning:

```bash
cd workshop/00_personal_todo
uv run alembic upgrade head
```

**Expected output (4 steps):**

```
INFO  [alembic.runtime.migration] Running upgrade  -> 2026_02_21_001, initial
INFO  [alembic.runtime.migration] Running upgrade 2026_02_21_001 -> 2026_02_21_002, add_updated_at_to_todos
INFO  [alembic.runtime.migration] Running upgrade 2026_02_21_002 -> 2026_02_21_003, add_deleted_at_to_todos
INFO  [alembic.runtime.migration] Running upgrade 2026_02_21_003 -> 2026_02_21_004, make_is_completed_not_nullable
INFO  [alembic.runtime.migration] Running upgrade 2026_02_21_004 -> head
```

Confirm in psql:
```bash
docker exec -it personal_todo_postgres psql -U todo_user -d todo_db -c '\dt'
# Should list: todos, alembic_version
```

---

## 7. Seed the Database (If Needed)

The new Postgres DB has no rows. The app's `seed_db()` seeds automatically when `Todo count == 0`. Simply start the app and it will seed on first run.

Or trigger seeding manually if you have a make target for it:
```bash
# If you start the app, seeding happens automatically on startup
make run
```

---

## 8. Start the App and Verify

```bash
make run
```

Open `http://localhost:8080/docs` — Swagger UI should be available and all endpoints should work, now backed by Postgres.

Quick smoke test:
```bash
# List todos
curl -s http://localhost:8080/todos | python3 -m json.tool

# Create a todo
curl -s -X POST http://localhost:8080/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "My first Postgres todo"}' | python3 -m json.tool
```

---

## 9. Day-to-Day — Makefile Commands

The Makefile is intentionally slim — just two commands for the DB lifecycle. Docker Compose handles all idempotency (already running, already stopped) internally.

| Command | Underlying call | What it does |
|---|---|---|
| `make db-start` | `docker compose up -d` | Starts the container; safe to call even if already running |
| `make db-stop` | `docker compose down` | Stops the container; data in `localdev/data/` is preserved |

**Normal daily workflow:**
```bash
make db-start   # morning: bring Postgres up
make run        # start the API
# ... work ...
make db-stop    # evening: stop Postgres (data safe)
```

**If you need to inspect the DB directly:**
```bash
# Open a psql shell
docker exec -it personal_todo_postgres psql -U todo_user -d todo_db

# Inside psql:
\dt                        -- list tables
SELECT COUNT(*) FROM todos; -- count rows
\q                         -- quit
```

---

## Troubleshooting

### `check_same_thread` TypeError at startup
You forgot Step 4. Remove `connect_args={"check_same_thread": False}` from `database.py`.

### `connection refused` on port 5432
```bash
docker ps | grep personal_todo_postgres   # check if container is running
make db-start                             # start it if stopped
```

### `ModuleNotFoundError: psycopg2`
```bash
uv add psycopg2-binary
```

### `FATAL: database "todo_db" does not exist`
Container was created with different env vars, or the data directory is stale. Wipe and recreate:
```bash
make db-stop
rm -rf localdev/data/personal_todo_pgdata
mkdir -p localdev/data/personal_todo_pgdata
make db-start
```

### Alembic: `Can't locate revision ...`
```bash
# Check current state
uv run alembic current
# Replay from scratch
uv run alembic upgrade head
```

### Tables exist but data is missing
Expected — the Postgres DB is fresh. Run `make run` to trigger auto-seeding.

---

## Concept Summary

| Concept | SQLite | PostgreSQL |
|---|---|---|
| Connection URL | `sqlite:///./database.db` | `postgresql+psycopg2://user:pass@host/db` |
| Threading arg | `check_same_thread=False` required | Not needed, remove it |
| ALTER TABLE | Not supported natively → `render_as_batch` workaround | Fully supported |
| Running | File on disk, no server | Server process (Docker container) |
| Data persistence | `.db` file | Bind mount at `localdev/data/personal_todo_pgdata/` (persists across `stop`/`start`) |
| Best for | Local prototyping, SQLite learning | Production-like dev, all future work |

---

*Created: 2026-02-22*
