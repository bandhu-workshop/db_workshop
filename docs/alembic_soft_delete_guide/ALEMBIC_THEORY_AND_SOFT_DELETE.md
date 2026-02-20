# Alembic Migration & Schema Management: Complete Guide

## Part 1: Theory - What is Alembic and Why Do We Need It?

### The Problem: Manual Schema Management is Dangerous ❌

Without migrations, managing database schemas becomes chaotic:

```
Team Member A: "I added a new column called `is_archived`"
Team Member B: "I added a column called `is_deleted`"
Production DB: "I have neither of these columns!"
QA Environment: "I have `is_archived` from 3 weeks ago, outdated structure..."
Local Dev 1: "My database crashed, let me recreate it... oh wait, columns changed!"
```

### The Solution: Alembic = Version Control for Your Database 🎯

**Alembic** is:
- A lightweight database migration tool for SQLAlchemy
- Version control for your database schema
- Tracks every change: add column, drop table, rename field, etc.
- Makes it easy to move forward (`upgrade`) or backward (`downgrade`)
- Team-friendly: all schema changes are in tracked migration files

Think of it like `git` but for your database schema.

---

## Part 2: Core Concepts

### A. What Happens During a Migration?

```
Working Code (models.py)
        ↓
SQLAlchemy ORM defines the schema
        ↓
Developer creates a migration file
        ↓
Migration scripts Python operations (add_column, drop_table, etc.)
        ↓
Alembic applies migration to database
        ↓
Database schema updated to match code
```

### B. Migration Files Structure

```
alembic/
├── versions/
│   ├── 001_add_users_table.py      ← Migration 1
│   ├── 002_add_email_to_users.py   ← Migration 2
│   └── 003_add_soft_delete.py      ← Migration 3 (we'll create this)
├── env.py                           ← How to connect to DB
├── script.py.mako                   ← Template for new migrations
└── alembic.ini                      ← Configuration
```

**Key Point**: Each migration is **incremental**. Migration 002 depends on 001, and 003 depends on 002.

### C. Three Types of Migrations

#### 1. **Automatic Migrations** (Recommended for Learning)
```python
alembic revision --autogenerate -m "add soft delete"
```
Alembic compares your SQLAlchemy models with the database and **auto-generates** the migration file. Fast, but less control.

#### 2. **Manual Migrations** (Full Control)
```python
alembic revision -m "add soft delete"
```
You write the migration code yourself. Slower, but fine-grained control. Preferred in production.

#### 3. **Empty/Downgrade Migrations** (Rollback)
```python
alembic downgrade -1
```
Reverses the last migration. Useful for debugging.

---

## Part 3: Industry Best Practices

### ✅ DO:

1. **Create one migration per feature/change**
   ```
   Good: 001_add_soft_delete_to_todos.py
   Bad:  001_add_soft_delete_and_rename_columns.py
   ```

2. **Always use timestamps or sequential numbering**
   ```
   Good: 2024_02_19_001_add_soft_delete.py
   Bad:  latest_schema.py
   ```

3. **Write descriptive migration names**
   ```
   Good: "add_deleted_at_column_with_default"
   Bad:  "fixes"
   ```

4. **Test migrations locally before pushing**
   ```bash
   alembic upgrade head  # Apply to local DB
   alembic downgrade -1  # Verify it rolls back
   alembic upgrade head  # Apply again to verify idempotency
   ```

5. **Always include a downgrade path**
   ```python
   def upgrade():
       op.add_column('todos', sa.Column('deleted_at', sa.DateTime(), nullable=True))
   
   def downgrade():
       op.drop_column('todos', 'deleted_at')
   ```

6. **Use batch operations for SQLite**
   ```python
   # SQLite doesn't support ALTER TABLE to add NOT NULL columns
   # So we use batch mode:
   with op.batch_alter_table('todos', schema=None) as batch_op:
       batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))
   ```

### ❌ DON'T:

1. ❌ Directly modify the database without a migration file
   ```
   # DON'T DO THIS:
   database.db> ALTER TABLE todos ADD COLUMN deleted_at DATETIME;
   # (Your code doesn't know about this change)
   ```

2. ❌ Modify migration files after they're committed
   ```
   # Once in git, migrations are immutable:
   ❌ git commit migration_001.py
   ❌ (2 weeks later) Edit migration_001.py
   
   ✅ Create migration_002.py to fix the issue instead
   ```

3. ❌ Skip version control for migrations
   ```
   # This defeats the whole purpose:
   .gitignore: alembic/versions/  ← DON'T DO THIS
   ```

4. ❌ Run migrations in multiple threads/processes simultaneously
   ```
   # Alembic uses database locks. Concurrent migrations = data corruption
   ❌ Run 5 parallel alembic upgrade commands
   ✅ Run them sequentially
   ```

5. ❌ Use raw SQL in migrations without testing
   ```python
   # This might work locally but fail in production:
   op.execute("UPDATE todos SET deleted_at = NOW() WHERE id > 0")
   
   # Better: Use SQLAlchemy operations that work across DBs
   op.execute(text("UPDATE todos SET deleted_at = :now WHERE id > 0"), {"now": func.now()})
   ```

---

## Part 4: How to Add a Column Following Best Practices

### 7-Step Workflow (Real Industry Practice)

### Step 1: Plan the Change
```
Requirement: Add soft delete feature to todos

What needs to change?
- Add `deleted_at` column (DateTime, nullable, default=None)
- Update Todo model with deleted_at field
- Update CRUD logic to filter out deleted items
- Create a migration file
- Test: upgrade → downgrade → upgrade again
```

### Step 2: Update the SQLAlchemy Model
```python
# models.py
from datetime import datetime
from sqlalchemy import DateTime

class Todo(Base):
    __tablename__ = "todos"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
    #                                                      ↑
    #                                       Only soft-deleted rows have a value
```

### Step 3: Initialize Alembic (One-Time Setup)
```bash
alembic init alembic
```
This creates the alembic directory structure.

### Step 4: Configure Alembic (alembic/env.py)
```python
# Tell Alembic how to connect to your database
from core.database import engine, Base

target_metadata = Base.metadata
```

### Step 5: Create the Migration File
```bash
alembic revision --autogenerate -m "add_deleted_at_to_todos"
```

This generates a file like: `alembic/versions/001_add_deleted_at_to_todos.py`

### Step 6: Review & Test the Migration
```python
# alembic/versions/001_add_deleted_at_to_todos.py

def upgrade():
    # For SQLite (batch mode required)
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
        )

def downgrade():
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')
```

Test locally:
```bash
alembic upgrade head      # Apply migration
alembic downgrade -1      # Rollback
alembic upgrade head      # Apply again (verify idempotency)
```

### Step 7: Update CRUD & API Logic
```python
# services/todo_crud.py
def get_todo(session: Session, todo_id: int) -> Todo | None:
    return session.query(Todo).filter(
        Todo.id == todo_id,
        Todo.deleted_at.is_(None)  # Only get non-deleted todos
    ).first()

def delete_todo(session: Session, todo_id: int) -> bool:
    todo_item = session.get(Todo, todo_id)
    if not todo_item:
        return False
    
    todo_item.deleted_at = datetime.utcnow()  # Soft delete
    session.commit()
    return True
```

---

## Part 5: Frequently Used Alembic Commands

### Core Commands (The 80/20 you'll use)

```bash
# 1. Create a new migration (auto-generate based on model changes)
alembic revision --autogenerate -m "describe what changed"

# 2. Create an empty migration (for manual control)
alembic revision -m "describe what changed"

# 3. Apply all pending migrations to database
alembic upgrade head

# 4. Apply specific number of migrations
alembic upgrade +1          # Apply 1 migration
alembic upgrade +3          # Apply 3 migrations

# 5. Rollback/Downgrade migrations
alembic downgrade -1        # Rollback 1 migration
alembic downgrade -3        # Rollback 3 migrations
alembic downgrade base      # Rollback all migrations

# 6. See current database version
alembic current

# 7. View migration history (what's been applied)
alembic history

# 8. See what will happen (dry run)
alembic upgrade head --sql  # Show SQL without executing

# 9. Show all available migrations
alembic branches            # Show all migration branches

# 10. Merge branches (if you have divergent migrations)
alembic merge              # Merge conflicting migration branches
```

### Advanced Commands (When You Need Them)

```bash
# Show detailed migration information
alembic history --verbose

# Go to a specific migration by revision ID
alembic upgrade abc1234

# Stamp the database as if migration was applied (don't use!)
# Only use if you manually modified database
alembic stamp head

# Edit the latest migration
alembic edit

# Show current migration
alembic current --verbose
```

---

## Part 6: Makefile Integration

Add these targets to your `Makefile` for easy migration management:

```makefile
# Database Migrations
db-init:
	@echo "Initializing Alembic..."
	uv run alembic init -t async alembic

db-migrate:
	@echo "Creating auto-migration..."
	uv run alembic revision --autogenerate -m "$(MESSAGE)"

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

db-reset:
	@echo "⚠️  WARNING: Reset database to initial state!"
	uv run alembic downgrade base
	uv run alembic upgrade head
	@echo "✅ Database reset complete"

db-test-migrations:
	@echo "Testing migrations (upgrade → downgrade → upgrade)..."
	uv run alembic upgrade head
	uv run alembic downgrade -1
	uv run alembic upgrade head
	@echo "✅ Migration test passed"
```

Usage:
```bash
make db-migrate MESSAGE="add soft delete to todos"
make db-upgrade
make db-downgrade
make db-history
```

---

## Part 7: Real-World Soft Delete Implementation

### Understanding Soft Delete

**Hard Delete** (What we have now):
```python
# This deletes the entire row from the database
session.delete(todo_item)
```

**Soft Delete** (What we're adding):
```python
# This just marks a row as deleted, data stays in DB
todo_item.deleted_at = datetime.utcnow()
```

**Why Soft Delete?**
- ✅ Recover accidentally deleted data
- ✅ Keep historical records for auditing
- ✅ Preserve foreign key relationships
- ✅ Analytics: "How many todos were deleted?"
- ❌ Slightly slower queries (need to filter out deleted rows)

### Implementation Checklist

- [ ] Step 1: Update `models.py` with `deleted_at` column
- [ ] Step 2: Initialize Alembic
- [ ] Step 3: Create migration with `alembic revision --autogenerate`
- [ ] Step 4: Apply migration with `alembic upgrade head`
- [ ] Step 5: Update CRUD functions to filter soft-deleted rows
- [ ] Step 6: Update `delete_todo()` to soft delete
- [ ] Step 7: Test: Create todo → Soft delete → Verify it's hidden
- [ ] Step 8: Add restore function (optional but useful)
- [ ] Step 9: Makefile integration
- [ ] Step 10: Commit migration files to git

---

## Summary Table: When to Use What

| Scenario | Command | Risk Level |
|----------|---------|-----------|
| Add a column | `alembic revision --autogenerate` | Low |
| Rename a column | Manual migration | Medium |
| Change column type | Manual migration | High |
| Drop a column | Manual migration | Critical |
| Add data constraint | Manual migration | Medium |
| Add an index | Auto or manual | Low |
| Delete a table | Manual migration | Critical |

---

## Common Gotchas & Solutions

### Gotcha 1: SQLite Doesn't Support Certain ALTER TABLE Operations
```python
# ❌ This fails on SQLite:
op.alter_column('todos', 'title', nullable=False)

# ✅ Use batch mode:
with op.batch_alter_table('todos') as batch_op:
    batch_op.alter_column('title', nullable=False)
```

### Gotcha 2: Migration Files Must Be Sequential
```
✅ 001_add_users.py → 002_add_email.py → 003_soft_delete.py
❌ 001_add_users.py → 003_soft_delete.py (missing 002!)
```

### Gotcha 3: Don't Manually Edit Applied Migrations
```
Once committed, migrations are immutable. Create a new migration instead.
```

### Gotcha 4: Always Test the Downgrade Path
```bash
alembic upgrade head     # Apply
alembic downgrade -1     # Verify rollback works
alembic upgrade head     # Verify upgrade works again
```

---

## Next Steps

You're now ready to:
1. Set up Alembic in your project
2. Create the soft delete migration
3. Update your CRUD logic
4. Test the entire workflow
5. Commit everything to git

Let's implement this! 🚀
