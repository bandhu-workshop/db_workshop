# Schema-Per-Project Setup

Migrating from "one database per project" to a shared `workshop_db` database where
each workshop project owns a dedicated PostgreSQL schema.

---

## Target Architecture

```
workshop_db  (single Postgres database)
├── schema: 00_personal_todo   ←  tables: todos, alembic_version
├── schema: 01_user_auth_todo  ←  tables: users, sessions, alembic_version
├── schema: 02_...             ←  ...
└── schema: public             ←  empty (Postgres default, leave alone)
```

Each project schema contains:
- Its own application tables
- Its own `alembic_version` table (migration history is isolated per project)

---

## Production Rule: Never Edit Applied Migrations

> **Golden rule**: Once a migration has been applied to any persistent environment
> (staging, production), it is immutable. You add a new migration forward—you never
> edit history.

### Why?

Alembic tracks history via revision IDs stored in `alembic_version`. If you edit a
migration file that was already run, the SQL it contains has already been executed.
Changing the file changes nothing on the live database—but it creates a dangerous
mismatch between what Alembic *thinks* happened and what *actually* happened.

### Two Paths

| Situation | Correct approach |
|---|---|
| Migrations already applied to staging/prod | Add a **new** migration that creates the schema and moves tables |
| Migrations only ever run locally (clean slate) | Edit existing files, wipe local DB, re-run from scratch |

**Our situation**: This is a local workshop database that has never been deployed
anywhere. We are on the clean-slate path. We will **edit existing migration files**
here — but only because we know with certainty they have never run against a
persistent environment.

---

## Files to Change

| # | File | What Changes |
|---|---|---|
| 1 | `docker-compose.yml` *(workspace root, new)* | Shared container, `POSTGRES_DB=workshop_db` |
| 2 | `Makefile` *(workspace root, new)* | `db-start` / `db-stop` targets for entire workshop |
| 3 | `00_personal_todo/docker-compose.yml` | Delete (no longer needed) |
| 4 | `app/core/config.py` | DB URL: `fastapi_db` → `workshop_db` |
| 5 | `app/models.py` | Add `__table_args__ = {"schema": "00_personal_todo"}` |
| 6 | `app/core/database.py` | `CREATE SCHEMA IF NOT EXISTS` before `create_all` |
| 7 | `alembic/env.py` | `search_path`, `version_table_schema`, `include_schemas` |
| 8 | `alembic/versions/001_initial.py` | Add `schema=` + `CREATE SCHEMA` op |
| 9 | `alembic/versions/002_*.py` | Add `schema=` to `add_column` / `drop_column` |
| 10 | `alembic/versions/003_*.py` | Add `schema=` to `add_column` / `drop_column` |
| 11 | `alembic/versions/004_*.py` | Add `schema=` to `batch_alter_table` |
| 12 | `localdev/data/` | Wipe old volume, start fresh |

---

## Step-by-Step

### Step 1 — Shared docker-compose + root Makefile

The Postgres container lives at the **workspace root** so it is shared across all
workshop projects. A single root-level `Makefile` provides `db-start`/`db-stop`
for the entire workshop — individual project Makefiles no longer need those targets.

**`docker-compose.yml` (workspace root):**

```yaml
services:
  postgres:
    image: postgres:16
    container_name: workshop_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-admin}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-admin123}
      POSTGRES_DB: ${POSTGRES_DB:-workshop_db}
    ports:
      - "5432:5432"
    volumes:
      - ./localdev/data/workshop_pgdata:/var/lib/postgresql/data
```

> **Volume path note**: Docker Compose resolves relative volume paths from the
> directory containing `docker-compose.yml`. Since the file is at the workspace
> root, `./localdev/data/workshop_pgdata` correctly maps to
> `<workspace>/localdev/data/workshop_pgdata`. Using `../../localdev/...` would
> resolve two levels *above* the workspace and store data outside the project.

**`Makefile` (workspace root):**

```makefile
# ── Postgres (Docker Compose) ─────────────────────────────────────────────────
db-start:
	@docker compose up -d

db-stop:
	@docker compose down
```

Because this Makefile sits next to `docker-compose.yml`, no `-f` flag is needed.

**Delete** `workshop/00_personal_todo/docker-compose.yml` — replaced by the root
compose file above. The project Makefile (`00_personal_todo/Makefile`) does **not**
need `db-start`/`db-stop` — those are now workspace-level concerns.

---

### Step 2 — `app/core/config.py`

Change the default database name in the connection URL:

```python
# BEFORE
DATABASE_URL: str = os.getenv(
    "POSTGRES_URL",
    "postgresql+psycopg2://admin:admin123@localhost:5432/fastapi_db",
)

# AFTER
DATABASE_URL: str = os.getenv(
    "POSTGRES_URL",
    "postgresql+psycopg2://admin:admin123@localhost:5432/workshop_db",
)
```

---

### Step 3 — `app/models.py`

Pin every model to its schema. SQLAlchemy will use this in all DDL and DML it
generates.

```python
# BEFORE
class Todo(Base):
    __tablename__ = "todos"

# AFTER
SCHEMA = "00_personal_todo"

class Todo(Base):
    __tablename__ = "todos"
    __table_args__ = {"schema": SCHEMA}
```

Defining `SCHEMA` as a module-level constant means all models in this project
reference the same string — one place to change it if needed.

---

### Step 4 — `app/core/database.py`

`create_all()` cannot create a table inside a schema that doesn't exist yet.
The schema must be created explicitly before table creation:

```python
from sqlalchemy import text

def init_db():
    import app.models  # noqa: F401

    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS \"00_personal_todo\""))
        conn.commit()

    Base.metadata.create_all(bind=engine)
    print("✅ Database tables initialized")
```

> **Note on quoting**: `00_personal_todo` starts with a digit. PostgreSQL requires
> identifiers starting with digits to be double-quoted. SQLAlchemy handles this
> automatically in model DDL, but raw SQL strings need the quotes explicitly.

---

### Step 5 — `alembic/env.py`

Three things must be configured for schema-aware migrations:

| Config key | Purpose |
|---|---|
| `SET search_path` | Unqualified names in migration SQL resolve to our schema, not `public` |
| `version_table_schema` | Alembic's own `alembic_version` table lives inside our schema (isolated per project) |
| `include_schemas=True` | Autogenerate compares all schemas, not just `public` |

```python
from sqlalchemy import text

SCHEMA = "00_personal_todo"

def run_migrations_online() -> None:
    connectable = engine

    with connectable.connect() as connection:
        # Ensure schema exists before migrations run
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
        connection.execute(text(f'SET search_path TO "{SCHEMA}", public'))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema=SCHEMA,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()
```

Apply the same `version_table_schema` and `include_schemas` to `run_migrations_offline()`.

---

### Step 6 — Migration file 001 (initial)

This is the most significant patch. Two things happen:

1. Add `op.execute("CREATE SCHEMA IF NOT EXISTS ...")` as the **very first statement**
   in `upgrade()`. This makes the migration self-contained — it can run against a
   brand-new database with no pre-existing schema.
2. Add `schema="00_personal_todo"` to every table/index operation.

```python
def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS "00_personal_todo"')  # <-- new

    op.create_table(
        "todos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="00_personal_todo",                                  # <-- new
    )
    op.create_index(
        op.f("ix_todos_id"),
        "todos",
        ["id"],
        unique=False,
        schema="00_personal_todo",                                  # <-- new
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_todos_id"),
        table_name="todos",
        schema="00_personal_todo",                                  # <-- new
    )
    op.drop_table("todos", schema="00_personal_todo")               # <-- new
    op.execute('DROP SCHEMA IF EXISTS "00_personal_todo" CASCADE')  # <-- new
```

> **Production pattern**: The `CREATE SCHEMA` in `upgrade()` and `DROP SCHEMA CASCADE`
> in `downgrade()` makes migration 001 fully self-contained and reversible — exactly
> how production migrations should work.

---

### Step 7 — Migration file 002 (add updated_at)

`op.add_column` and `op.drop_column` both accept a `schema` keyword argument:

```python
def upgrade() -> None:
    op.add_column(
        "todos",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="00_personal_todo",    # <-- new
    )

def downgrade() -> None:
    op.drop_column("todos", "updated_at", schema="00_personal_todo")  # <-- new
```

---

### Step 8 — Migration file 003 (add deleted_at)

Same pattern as 002:

```python
def upgrade() -> None:
    op.add_column(
        "todos",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="00_personal_todo",    # <-- new
    )

def downgrade() -> None:
    op.drop_column("todos", "deleted_at", schema="00_personal_todo")  # <-- new
```

---

### Step 9 — Migration file 004 (alter column)

`op.batch_alter_table` is normally a SQLite workaround for `ALTER COLUMN`. With
PostgreSQL, `op.alter_column` is the correct, simpler form. However, since this
migration was auto-generated with `batch_alter_table`, we keep it as-is for history
fidelity and just add the `schema` argument:

```python
def upgrade() -> None:
    with op.batch_alter_table("todos", schema="00_personal_todo") as batch_op:  # <-- schema added
        batch_op.alter_column(
            "is_completed",
            existing_type=sa.Boolean(),
            nullable=False,
        )

def downgrade() -> None:
    with op.batch_alter_table("todos", schema="00_personal_todo") as batch_op:  # <-- schema added
        batch_op.alter_column(
            "is_completed",
            existing_type=sa.Boolean(),
            nullable=True,
        )
```

---

### Step 10 — Wipe old data volume and re-run

Since we changed the database name and schema structure, the old volume
(`localdev/data/personal_todo_pgdata/`) is incompatible. Delete it and start fresh.
All `docker compose` commands run from the **workspace root** where
`docker-compose.yml` lives (or use `make db-start` / `make db-stop`):

```bash
# From workspace root — stop the container
make db-stop
# or: docker compose down

# Wipe old data (old DB, wrong name and structure)
rm -rf localdev/data/personal_todo_pgdata/

# Start fresh (Postgres initialises workshop_db from scratch)
make db-start
# or: docker compose up -d

# Run all migrations (from the project directory)
cd workshop/00_personal_todo
uv run alembic upgrade head

# Verify
uv run alembic current
# Should show: 2026_02_21_004 (head)
```

---

## Verification Checklist

```
[ ] docker ps  →  container "workshop_postgres" running
[ ] pgAdmin shows workshop_db → Schemas → 00_personal_todo → Tables → todos
[ ] pgAdmin shows 00_personal_todo.alembic_version (NOT public.alembic_version)
[ ] alembic current  →  2026_02_21_004 (head)
[ ] alembic history --verbose  →  all 4 revisions listed
[ ] FastAPI /todos endpoint works (app still reads/writes correctly)
```

---

## Convention for Future Projects

Every new workshop project follows this pattern:

1. `models.py` — `__table_args__ = {"schema": "<project_folder_name>"}`
2. `alembic/env.py` — `SCHEMA = "<project_folder_name>"`, same env.py template
3. `001_initial.py` — First line of `upgrade()` is always `CREATE SCHEMA IF NOT EXISTS`
4. No per-project `docker-compose.yml` — all projects share the root `docker-compose.yml`
5. No per-project `db-start`/`db-stop` in Makefile — use `make db-start` from the workspace root

---

*Created: 2026-02-24*
