# Initializing Alembic with Existing Database & Data

## Your Situation

✅ You have:
- Existing database (`database.db`) with data already in it
- SQLAlchemy models defined (`models.py`)
- Alembic initialized but no migrations yet

❌ You DON'T have:
- Any migration files in `alembic/versions/`
- History of how the schema was created

**Goal:** Create the initial migration that captures current schema, then move forward from there.

---

## Solution: 3-Step Process

### Step 1: Create the Initial/Baseline Migration

This migration will capture your **entire current schema**:

```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo

# Create initial migration that mirrors current database
uv run alembic revision --autogenerate -m "initial_migration_baseline"
```

**What happens:**
1. Alembic compares your SQLAlchemy models vs database
2. Since DB already has tables, it creates an `upgrade()` that creates all tables
3. This becomes your "baseline" (starting point for all future migrations)

**Expected output:**
```
  Generating /home/db/Work/db_workshop/workshop/00_personal_todo/alembic/versions/2025_02_20_001_initial_migration_baseline.py ...  done
```

---

### Step 2: Inspect the Generated Migration

Look at what was created:

```bash
cat alembic/versions/2025_02_20_001_initial_migration_baseline.py
```

**Expected content:**
```python
"""initial_migration_baseline

Revision ID: 2025_02_20_001
Revises: 
Create Date: 2025-02-20 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '2025_02_20_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CREATE TABLE todos
    op.create_table(
        'todos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # CREATE TABLE todo_idempotency_keys
    op.create_table(
        'todo_idempotency_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('idempotency_key', sa.String(length=50), nullable=False),
        sa.Column('todo_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['todo_id'], ['todos.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key')
    )


def downgrade() -> None:
    op.drop_table('todo_idempotency_keys')
    op.drop_table('todos')
```

✅ **This looks correct!** It captures your entire current schema.

---

### Step 3: Mark Database as "At This Version"

Now you need to tell Alembic: "The database is already at this schema, don't apply this migration, just mark it as applied."

Use the `stamp` command:

```bash
# Tell Alembic: "Current database state = revision 2025_02_20_001"
uv run alembic stamp 2025_02_20_001
```

**What this does:**
1. Creates the `alembic_version` table in your database
2. Sets it to `2025_02_20_001` (your initial migration)
3. Now Alembic knows: "The DB has all tables from this migration"
4. Future migrations start FROM here

**Verify it worked:**

```bash
uv run alembic current
```

Expected output:
```
2025_02_20_001
```

And check the database:
```bash
sqlite3 database.db ".tables"
```

Should show:
```
alembic_version  todo_idempotency_keys  todos
```

✅ **Perfect!** Your database is now tracked by Alembic.

---

## ✅ You're Now Ready to Move Forward!

Your database:
- ✅ Has all the existing data (unchanged)
- ✅ Is marked as "at version 2025_02_20_001"
- ✅ Can now be tracked with migrations

### Moving Forward: Adding Soft Delete

Now that you have the baseline, adding soft delete is easy:

#### Step 1: Update models.py

Add the `deleted_at` column:

```python
class Todo(Base):
    __tablename__ = "todos"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # ADD THIS:
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
```

#### Step 2: Create the migration (now it's easy!)

```bash
uv run alembic revision --autogenerate -m "add_soft_delete_to_todos"
```

Alembic will create a migration that ONLY adds the `deleted_at` column (not the whole schema again).

#### Step 3: Apply the migration

```bash
uv run alembic upgrade head
```

Done! ✅

---

## Visual Timeline: What Happened

```
Time 0: Database created manually (no migrations)
        ├─ todos table exists
        ├─ todo_idempotency_keys table exists
        └─ Some data in tables

Time 1: Initialize Alembic
        └─ Create initial migration capturing schema

Time 2: Stamp database
        └─ Mark: "DB is at initial_migration_baseline"

Time 3: From now on, use normal migration workflow
        ├─ Modify models.py
        ├─ Create migration (auto-generate)
        ├─ Review migration
        └─ Apply migration (alembic upgrade head)
```

---

## Commands You Just Ran (Reference)

```bash
# 1. Init Alembic (already done)
alembic init alembic

# 2. Configure env.py (already done)
# Edit alembic/env.py to import Base

# 3. Create initial migration (captures current schema)
alembic revision --autogenerate -m "initial_migration_baseline"

# 4. Stamp database (mark it as "at this version")
alembic stamp 2025_02_20_001

# 5. Verify
alembic current         # Should show your revision ID
alembic history         # Should show the initial migration
```

---

## Important: The Stamp Command

**What is `alembic stamp`?**

It tells Alembic: "The database is already at this version." It doesn't apply the migration—it just records in the database that the migration was applied.

**Why do we need it?**

Because your database already has the schema from the initial migration. If you ran `alembic upgrade head`, it would try to create tables that already exist → error! So we use `stamp` to skip that.

**When to use it:**
- ✅ When you have an existing database with data
- ✅ Creating the baseline initial migration
- ❌ Never for normal migrations (use upgrade/downgrade)

---

## Troubleshooting: Common Issues

### Issue 1: "Table already exists" error
```bash
# You ran: alembic upgrade head
# Got: sqlalchemy.exc.OperationalError: table todos already exists

# Solution: Use stamp instead
alembic downgrade base          # Undo if applied
alembic stamp 2025_02_20_001    # Mark as applied without running
```

### Issue 2: "No changes detected"
```bash
# Problem: You created migration but initial migration is empty

# Solution: Check if models.py matches database schema
# If they match, that's fine! The initial migration is just a baseline.
```

### Issue 3: Forgot to stamp, already applied migration
```bash
# You ran: alembic upgrade head
# Now DB has duplicate tables

# Solution: Downgrade then stamp
alembic downgrade base
alembic stamp 2025_02_20_001
```

---

## The CORRECT Workflow from Now On

**This is what you do for EVERY future change:**

```bash
# 1. Modify models.py (add new column, table, etc.)
# (example: add deleted_at column)

# 2. Create auto-generated migration
uv run alembic revision --autogenerate -m "add_soft_delete"

# 3. Review the migration
cat alembic/versions/2025_02_20_002_add_soft_delete.py

# 4. Apply it
uv run alembic upgrade head

# 5. Verify
sqlite3 database.db ".schema todos"

# 6. Commit
git add alembic/versions/2025_02_20_002_add_soft_delete.py
git commit -m "feat: add soft delete feature"
```

✅ **From now on, migration tracking is automatic!**

---

## Makefile Shortcuts (Add These)

```makefile
# Database Migrations
db-init:
	@echo "Initializing Alembic..."
	uv run alembic init alembic

db-baseline:
	@echo "Creating baseline migration from existing database..."
	uv run alembic revision --autogenerate -m "initial_baseline"
	@echo "Review the migration, then run: make db-stamp"

db-stamp:
	@echo "Stamping database as at current version..."
	@read -p "Enter revision ID (check alembic history): " rev; \
	uv run alembic stamp $$rev
	@echo "✅ Done"

db-migrate:
	@echo "Creating new migration..."
	@read -p "Enter migration description: " desc; \
	uv run alembic revision --autogenerate -m "$$desc"

db-upgrade:
	@echo "Applying migrations..."
	uv run alembic upgrade head

db-status:
	@echo "Current version:"
	@uv run alembic current
	@echo ""
	@echo "History:"
	@uv run alembic history

.PHONY: db-init db-baseline db-stamp db-migrate db-upgrade db-status
```

Usage:
```bash
make db-baseline    # Create initial migration
make db-stamp       # Stamp existing database
make db-migrate     # Create future migrations
make db-upgrade     # Apply migrations
make db-status      # Check status
```

---

## Quick Checklist: You're Set Up When...

- [ ] You have existing database with data
- [ ] You created initial migration: `2025_02_20_001_initial_migration_baseline.py`
- [ ] You stamped the database: `alembic stamp 2025_02_20_001`
- [ ] You verified: `alembic current` shows the revision ID
- [ ] You verified: `alembic history` shows the initial migration
- [ ] Moving forward: future changes use normal workflow

---

## Visual: Before vs After

### BEFORE (No Alembic)
```
database.db (existing, with data)
            ↓ (how did it get like this? Nobody knows!)
models.py
            ↓ (manual changes, risky)
database.db (out of sync?)
```

### AFTER (With Alembic)
```
database.db (existing, with data)
     ↓
alembic stamp [revision]  ← Baseline established
     ↓
alembic/versions/001_initial.py  ← Now tracked
     ↓
models.py (change)
     ↓
alembic revision --autogenerate (generate migration)
     ↓
alembic/versions/002_next_change.py  ← Tracked
     ↓
alembic upgrade head (apply to database)
     ↓
database.db (updated, tracked, reproducible)
```

---

## Key Points to Remember

1. **Your data is safe** - `stamp` doesn't modify the database schema, only records version
2. **Initial migration is a baseline** - It captures your entire current schema
3. **From now on, normal workflow** - Modify models → auto-generate → apply
4. **Always track migration files in git** - They're source code now
5. **stamp vs upgrade** - Use stamp once for baseline, upgrade for everything else

---

## Summary

You've successfully:
1. ✅ Created initial migration from existing database
2. ✅ Stamped the database to mark current state
3. ✅ Set up baseline for future migrations
4. ✅ Can now move forward safely

**From this point, every schema change:**
- Modify models.py
- Run `alembic revision --autogenerate`
- Run `alembic upgrade head`
- Commit the migration file

You're now using industry-standard database versioning! 🎉
