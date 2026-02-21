# Soft Delete Implementation: Step-by-Step Guide

Your project: `/home/db/Work/db_workshop/workshop/00_personal_todo`

## Current State

- ✅ Database: SQLite (`database.db`)
- ✅ ORM: SQLAlchemy
- ✅ API Framework: FastAPI
- ⚠️ Migrations: **NOT SET UP YET** (we'll add Alembic)

---

## Steps to Implement Soft Delete

### Phase 1: Setup Alembic (One-Time)

#### Step 1.1: Initialize Alembic in the project

```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo
uv run alembic init alembic
```

This creates:
```
00_personal_todo/
├── alembic.ini        ← Configuration (at project root)
└── alembic/
    ├── versions/          ← Migration files will go here
    ├── env.py             ← Database connection config
    └── script.py.mako     ← Template for new migrations
```

#### Step 1.2: Configure `alembic/env.py`

Edit the generated `alembic/env.py` to:
```python
# Find the line: target_metadata = None
# Replace it with:

from app.core.database import Base
target_metadata = Base.metadata
```

Also find the `get_engine()` function and replace it:
```python
def get_engine():
    from app.core.database import engine
    return engine
```

#### Step 1.3: Configure `alembic.ini`

Edit `alembic.ini` and find the line:
```ini
sqlalchemy.url = driver://user:password@localhost/dbname
```

Replace with:
```ini
sqlalchemy.url = 
# (Leave empty - env.py will handle it)
```

---

### Phase 2: Update Models

#### Step 2.1: Modify `app/models.py` to add `deleted_at` column

Add these lines to the `Todo` class:

```python
from datetime import datetime

# In the Todo class, add this column:
deleted_at = Column(
    DateTime(timezone=True),
    nullable=True,
    default=None,
)
```

Full updated `app/models.py`:
```python
from app.core.database import Base
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)


class Todo(Base):
    """
    Model for a TODO with soft delete support.
    """

    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TodoIdempotency(Base):
    """
    Stores idempotency keys to deduplicate POST requests.
    """

    __tablename__ = "todo_idempotency_keys"

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(50), unique=True, nullable=False, index=True)
    todo_id = Column(Integer, ForeignKey("todos.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
```

---

### Phase 3: Create the Migration

#### Step 3.1: Generate migration file

```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo
uv run alembic revision --autogenerate -m "add_soft_delete_to_todos"
```

This creates: `alembic/versions/001_add_soft_delete_to_todos.py`

#### Step 3.2: Review the generated migration

The file should look like this (for SQLite, it uses batch mode):

```python
"""Add soft delete to todos

Revision ID: abc1234def
Revises: 
Create Date: 2024-02-19 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'abc1234def'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Using batch mode for SQLite compatibility
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')
```

---

### Phase 4: Apply the Migration

#### Step 4.1: Apply migration to database

```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo
uv run alembic upgrade head
```

Expected output:
```
INFO [alembic.runtime.migration] Context impl SQLiteImpl.
INFO [alembic.runtime.migration] Will assume non-transactional DDL.
INFO [alembic.runtime.migration] Running upgrade  -> abc1234def, add_soft_delete_to_todos
```

#### Step 4.2: Verify migration was applied

```bash
uv run alembic current
```

Should show your migration revision ID.

#### Step 4.3: Test the rollback (IMPORTANT!)

```bash
uv run alembic downgrade -1
uv run alembic upgrade head
```

This verifies:
- ✅ Downgrade works
- ✅ Upgrade works
- ✅ Migration is idempotent

---

### Phase 5: Update CRUD Functions

#### Step 5.1: Update `app/services/todo_crud.py`

Modify the CRUD functions to handle soft deletes:

```python
"""
CRUD LAYER with Soft Delete Support

Key Changes:
- All READ operations filter out deleted items (deleted_at IS NULL)
- delete_todo() now soft deletes (sets deleted_at = now)
- No hard deletes anymore (data is preserved)
"""

from datetime import datetime
from app.models import Todo, TodoIdempotency
from app.schemas import TodoCreate, TodoUpdate
from sqlalchemy.orm import Session


def get_todo_by_idempotency_key(session: Session, idempotency_key: str) -> Todo | None:
    """Check cache, filter soft-deleted items."""
    record = (
        session.query(TodoIdempotency)
        .filter(TodoIdempotency.idempotency_key == idempotency_key)
        .first()
    )

    if record:
        todo = session.get(Todo, record.todo_id)
        # Ensure we don't return soft-deleted todos
        if todo and todo.deleted_at is None:
            return todo
    return None


def create_todo(session: Session, todo: TodoCreate) -> Todo:
    todo_item = Todo(**todo.model_dump())
    session.add(todo_item)
    session.commit()
    session.refresh(todo_item)
    return todo_item


def create_todo_with_idempotency(
    session: Session,
    todo: TodoCreate,
    idempotency_key: str | None = None,
) -> tuple[Todo, bool]:
    """Create todo with idempotency, respecting soft deletes."""
    
    if idempotency_key:
        cached_todo = get_todo_by_idempotency_key(session, idempotency_key)
        if cached_todo:
            return cached_todo, False

    todo_item = Todo(**todo.model_dump())
    session.add(todo_item)
    session.commit()
    session.refresh(todo_item)

    if idempotency_key:
        idempotency_record = TodoIdempotency(
            idempotency_key=idempotency_key,
            todo_id=todo_item.id,
        )
        session.add(idempotency_record)
        session.commit()

    return todo_item, True


def get_todo(session: Session, todo_id: int) -> Todo | None:
    """Get todo, but NOT if it's soft-deleted."""
    todo = session.get(Todo, todo_id)
    # Return None if todo doesn't exist or is soft-deleted
    if todo and todo.deleted_at is None:
        return todo
    return None


def get_all_todos(session: Session, include_deleted: bool = False) -> list[Todo]:
    """Get all todos, optionally including soft-deleted ones."""
    query = session.query(Todo)
    if not include_deleted:
        query = query.filter(Todo.deleted_at.is_(None))
    return query.all()


def update_todo(session: Session, todo_id: int, todo: TodoUpdate) -> Todo | None:
    """Update todo, but NOT if it's soft-deleted."""
    todo_item = session.get(Todo, todo_id)
    if not todo_item or todo_item.deleted_at is not None:
        return None

    for key, value in todo.model_dump(exclude_unset=True).items():
        setattr(todo_item, key, value)

    session.commit()
    session.refresh(todo_item)
    return todo_item


def delete_todo(session: Session, todo_id: int) -> bool:
    """Soft delete: mark todo as deleted instead of removing it."""
    todo_item = session.get(Todo, todo_id)
    if not todo_item:
        return False

    # Soft delete: set deleted_at timestamp
    todo_item.deleted_at = datetime.utcnow()
    session.commit()
    return True


def restore_todo(session: Session, todo_id: int) -> Todo | None:
    """Restore a soft-deleted todo."""
    todo_item = session.get(Todo, todo_id)
    if not todo_item:
        return None

    todo_item.deleted_at = None
    session.commit()
    session.refresh(todo_item)
    return todo_item


def purge_todo(session: Session, todo_id: int) -> bool:
    """Hard delete: permanently remove todo from database.
    
    Use sparingly! Only for compliance (GDPR right-to-be-forgotten, etc).
    """
    todo_item = session.get(Todo, todo_id)
    if not todo_item:
        return False

    session.delete(todo_item)
    session.commit()
    return True
```

---

### Phase 6: Update API Routes (Optional but Recommended)

#### Step 6.1: Add restore endpoint to `app/api/todo_api.py`

Add this route to support restoring deleted todos:

```python
@router.post(
    "/{todo_id}/restore",
    response_model=TodoResponse,
    status_code=200,
)
def restore_todo_endpoint(
    todo_id: int,
    session: Session = Depends(get_db),
):
    """Restore a soft-deleted todo."""
    from app.services.todo_crud import restore_todo
    
    todo_item = restore_todo(session, todo_id)
    if not todo_item:
        raise HTTPException(
            status_code=404, detail=f"TODO item not found with id {todo_id}"
        )
    return todo_item
```

---

### Phase 7: Update Schemas (Optional but Recommended)

#### Step 7.1: Add `deleted_at` to `TodoResponse` in `app/schemas.py`

```python
from datetime import datetime

class TodoResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    is_completed: bool
    deleted_at: datetime | None = None  # NEW
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

### Phase 8: Update Makefile

#### Step 8.1: Add Makefile targets for migrations

Add to `/home/db/Work/db_workshop/workshop/00_personal_todo/Makefile`:

```makefile
# Database Migrations
db-init:
	@echo "Initializing Alembic..."
	uv run alembic init -t async alembic

db-migrate:
	@echo "Creating auto-migration..."
	@read -p "Enter migration description: " desc; \
	uv run alembic revision --autogenerate -m "$$desc"

db-upgrade:
	@echo "Applying migrations..."
	uv run alembic upgrade head

db-downgrade:
	@echo "Rolling back last migration..."
	uv run alembic downgrade -1

db-history:
	@echo "Migration history..."
	uv run alembic history

db-current:
	@echo "Current database version..."
	uv run alembic current

db-test:
	@echo "Testing migration (up → down → up)..."
	uv run alembic upgrade head
	uv run alembic downgrade -1
	uv run alembic upgrade head
	@echo "✅ Migration test passed"

db-reset:
	@echo "⚠️  Resetting database to initial state..."
	uv run alembic downgrade base
	uv run alembic upgrade head
	@echo "✅ Database reset complete"
```

Updated full Makefile:
```makefile
# Format and type checking
check_format:
	@echo "Checking format..."
	uv run ruff check && uv tool run ruff format --check

check_type:
	@echo "Checking types..."
	uv run mypy --package workshop

format:
	@echo "Formatting code..."
	uv tool run ruff check --fix && uv tool run ruff format

run:
	@echo "Starting API server..."
	uv run python -m uvicorn main:app --host 0.0.0.0 --port=8080 --reload

# Database Migrations
db-init:
	@echo "Initializing Alembic..."
	uv run alembic init alembic

db-migrate:
	@echo "Creating auto-migration..."
	@read -p "Enter migration description: " desc; \
	uv run alembic revision --autogenerate -m "$$desc"

db-upgrade:
	@echo "Applying migrations..."
	uv run alembic upgrade head

db-downgrade:
	@echo "Rolling back last migration..."
	uv run alembic downgrade -1

db-history:
	@echo "Migration history..."
	uv run alembic history

db-current:
	@echo "Current database version..."
	uv run alembic current

db-test:
	@echo "Testing migration (up → down → up)..."
	uv run alembic upgrade head
	uv run alembic downgrade -1
	uv run alembic upgrade head
	@echo "✅ Migration test passed"

db-reset:
	@echo "⚠️  Resetting database to initial state..."
	uv run alembic downgrade base
	uv run alembic upgrade head
	@echo "✅ Database reset complete"

.PHONY: check_format check_type format run db-init db-migrate db-upgrade db-downgrade db-history db-current db-test db-reset
```

---

## Quick Reference: All Commands

```bash
# **Setup (run once)**
make db-init

# **Create a new migration**
make db-migrate
# Prompts for description, e.g., "add soft delete to todos"

# **Apply migrations**
make db-upgrade

# **Rollback last migration**
make db-downgrade

# **View migration history**
make db-history

# **Check current database version**
make db-current

# **Test migrations (verify up/down/up works)**
make db-test

# **Reset database completely**
make db-reset
```

---

## Testing Soft Delete (Manual Testing)

After applying migration, test with curl or your API client:

```bash
# 1. Create a todo
curl -X POST http://localhost:8080/todos \
  -H "Content-Type: application/json" \
  -d '{"title":"Test TODO","description":"Testing soft delete"}'

# Expected response:
# {
#   "id": 1,
#   "title": "Test TODO",
#   "description": "Testing soft delete",
#   "is_completed": false,
#   "deleted_at": null,
#   "created_at": "2024-02-19T10:30:00+00:00"
# }

# 2. Soft delete the todo
curl -X DELETE http://localhost:8080/todos/1

# 3. Try to get the deleted todo
curl http://localhost:8080/todos/1

# Expected: 404 Not Found (soft-deleted todos are hidden)

# 4. Restore the todo (optional)
curl -X POST http://localhost:8080/todos/1/restore
```

---

## Files to Modify Checklist

- [ ] `alembic/` directory (created by `make db-init`)
- [ ] `app/models.py` - Add `deleted_at` column
- [ ] `app/services/todo_crud.py` - Update CRUD functions
- [ ] `app/api/todo_api.py` - Add restore endpoint (optional)
- [ ] `app/schemas.py` - Add `deleted_at` to response (optional)
- [ ] `Makefile` - Add migration targets

---

## Common Commands You'll Use

| Goal | Command |
|------|---------|
| Create a new migration | `make db-migrate` |
| Apply all pending migrations | `make db-upgrade` |
| Rollback 1 migration | `make db-downgrade` |
| See all migrations | `make db-history` |
| Reset database | `make db-reset` |
| Test migrations work | `make db-test` |

---

## Troubleshooting

### Problem: "alembic: command not found"
```bash
# Solution: Use uv run
uv run alembic --version
# or add to Makefile and use: make db-current
```

### Problem: Migration fails with "no such table"
```bash
# Solution: Alembic needs to know about your DB
# Edit alembic/env.py to import Base correctly (see Step 1.2)
```

### Problem: "Column already exists"
```bash
# Solution: Migration already applied
# Check: make db-history
```

### Problem: Can't rollback (downgrade)
```bash
# Solution: Check that downgrade() function is in the migration file
# It should drop the column
def downgrade():
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')
```

---

## Next: Commit to Git

```bash
# Add migration files to git
git add alembic/versions/
git add alembic/env.py
git add alembic/alembic.ini

# Commit
git commit -m "feat: add soft delete feature to todos"
```

**Golden Rule**: Always commit migration files! They are source code now, not generated files.

---

## Summary

You now have:
✅ Alembic migrations set up
✅ Soft delete feature implemented
✅ Easy rollback capability
✅ Makefile shortcuts for common tasks
✅ Production-ready schema management

Next time you need to modify the schema:
```bash
make db-migrate  # Create migration
make db-upgrade  # Apply it
make db-test     # Verify it works
git add alembic/ && git commit -m "..."
```

That's it! 🚀
