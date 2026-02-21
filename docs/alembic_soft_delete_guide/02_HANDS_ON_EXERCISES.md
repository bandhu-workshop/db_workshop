# Alembic Hands-On Learning: Interactive Exercises

This guide walks you through **exactly** what commands to run, what files get created, and what to expect at each step.

---

## Exercise 1: Initialize Alembic

### Command:
```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo
uv run alembic init alembic
```

### What happens:
1. Alembic creates the `alembic/` directory
2. Creates subdirectories and files
3. Generates `alembic.ini` (configuration)
4. Generates `alembic/env.py` (connection config)

### Verify it worked:
```bash
ls -la alembic/
```

### Expected output:
```
total 24
drwxr-xr-x  4 db db 4096 Feb 19 10:00 .
drwxr-xr-x 10 db db 4096 Feb 19 10:00 ..
-rw-r--r--  1 db db 1234 Feb 19 10:00 env.py
-rw-r--r--  1 db db 5678 Feb 19 10:00 script.py.mako
drwxr-xr-x  2 db db 4096 Feb 19 10:00 versions
```

### What each file does:
- `env.py` = How to connect to database (we'll configure this)
- `script.py.mako` = Template for generating new migrations
- `versions/` = Directory where migration files go
- `alembic.ini` = Configuration file

---

## Exercise 2: Configure `alembic/env.py`

This is the crucial step! We need to tell Alembic how to connect to your database and find your SQLAlchemy models.

### Step 1: Open the file

```bash
cat alembic/env.py
```

You'll see ~80 lines of code. The important parts are:

```python
# Line 1: Import section
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Line 15-20: Get the configuration
config = context.config

# Line 25: THIS IS IMPORTANT - currently set to None
target_metadata = None
```

### Step 2: What we need to change

We need to:
1. Import `Base` from your `core.database` module
2. Set `target_metadata = Base.metadata` (instead of None)
3. Make sure migrations use YOUR database connection

### Step 3: Edit the file

Find this section in `alembic/env.py` (around line 20-25):

```python
from alembic import context

config = context.config
target_metadata = None
```

**Change it to:**

```python
from alembic import context
from app.core.database import Base  # ADD THIS LINE

config = context.config
target_metadata = Base.metadata  # CHANGE FROM None TO Base.metadata
```

### Step 4: Verify the change

```bash
grep "target_metadata" alembic/env.py
```

Should show:
```
target_metadata = Base.metadata
```

---

## Exercise 3: Check Current Database State

Before creating migrations, let's see what tables currently exist.

### Check the database:
```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo
sqlite3 database.db ".tables"
```

### Expected output:
```
alembic_version  todo_idempotency_keys  todos
```

**Understanding the output:**
- `alembic_version` = Table that Alembic creates to track migrations
- `todo_idempotency_keys` = Your custom table
- `todos` = Your custom table

### Check the todos table structure:
```bash
sqlite3 database.db ".schema todos"
```

### Expected output:
```sql
CREATE TABLE todos (
	id INTEGER NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT, 
	is_completed BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id)
);
```

**Notice: There's NO `deleted_at` column yet!** (We'll add it with a migration)

---

## Exercise 4: Create the First Migration (Manual)

Let's create a migration file manually to understand the structure.

### Step 1: Create the migration (empty)

```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo
uv run alembic revision -m "add_deleted_at_column"
```

### What happens:
Alembic creates a new migration file with a unique ID. 

### Expected output:
```
  Generating /home/db/Work/db_workshop/workshop/00_personal_todo/alembic/versions/abc1234def_add_deleted_at_column.py ...  done
```

The `abc1234def` is Alembic's way of giving each migration a unique ID.

### Step 2: List the migrations

```bash
ls alembic/versions/
```

### Expected output:
```
abc1234def_add_deleted_at_column.py
```

### Step 3: Look at the generated file

```bash
cat alembic/versions/abc1234def_add_deleted_at_column.py
```

### Expected output:
```python
"""add_deleted_at_column

Revision ID: abc1234def
Revises: 
Create Date: 2024-02-19 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# Metadata about this migration
revision = 'abc1234def'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # YOUR CODE HERE - what to do when applying
    pass


def downgrade():
    # YOUR CODE HERE - what to do when rolling back
    pass
```

**Key observations:**
1. `revision = 'abc1234def'` = Unique ID for this migration
2. `down_revision = None` = This is the first migration (nothing before it)
3. `def upgrade()` = Empty function (we need to fill this in)
4. `def downgrade()` = Empty function (we need to fill this in)

---

## Exercise 5: Edit the Migration File

Now let's add the actual code to add the `deleted_at` column.

### The goal:
Add a `deleted_at` column to the `todos` table.

### Step 1: Open the migration file for editing

```bash
cat alembic/versions/abc1234def_add_deleted_at_column.py
```

### Step 2: Replace the upgrade() function

**Find this:**
```python
def upgrade():
    # YOUR CODE HERE
    pass
```

**Replace with this:**
```python
def upgrade():
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
        )
```

**Why `batch_alter_table`?**
- SQLite doesn't support some ALTER TABLE operations
- Batch mode creates a temporary table, copies data, renames it back
- Works on all databases

### Step 3: Replace the downgrade() function

**Find this:**
```python
def downgrade():
    # YOUR CODE HERE
    pass
```

**Replace with this:**
```python
def downgrade():
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')
```

### Step 4: Verify the changes

```bash
cat alembic/versions/abc1234def_add_deleted_at_column.py
```

Should show your upgrade() and downgrade() functions filled in.

---

## Exercise 6: Preview Migration as SQL (Dry Run)

Before applying the migration, let's see what SQL will be executed.

### Command:
```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo
uv run alembic upgrade head --sql
```

### Expected output:
```sql
-- Running upgrade abc1234def -> (head)

BEGIN;

CREATE TABLE todos__new AS SELECT id, title, description, is_completed, created_at FROM todos;
DROP TABLE todos;
CREATE TABLE todos (id INTEGER NOT NULL, title VARCHAR(255) NOT NULL, description TEXT, is_completed BOOLEAN NOT NULL, created_at DATETIME NOT NULL, deleted_at DATETIME, PRIMARY KEY (id));
INSERT INTO todos (id, title, description, is_completed, created_at) SELECT id, title, description, is_completed, created_at FROM todos__new;
DROP TABLE todos__new;
UPDATE alembic_version SET version_num='abc1234def' WHERE alembic_version.zetag = 1;

COMMIT;
```

**What's happening:**
1. `CREATE TABLE todos__new` = Create temporary table with old columns
2. `DROP TABLE todos` = Remove old table
3. `CREATE TABLE todos` = Create new table WITH the `deleted_at` column
4. `INSERT INTO todos` = Copy data from temp table to new table
5. `DROP TABLE todos__new` = Remove temp table
6. `UPDATE alembic_version` = Mark this migration as applied

---

## Exercise 7: Actually Apply the Migration

Now let's apply it for real!

### Command:
```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo
uv run alembic upgrade head
```

### Expected output:
```
INFO [alembic.runtime.migration] Context impl SQLiteImpl.
INFO [alembic.runtime.migration] Will assume non-transactional DDL.
INFO [alembic.runtime.migration] Running upgrade  -> abc1234def, add_deleted_at_column
```

### Verify it worked:
```bash
sqlite3 database.db ".schema todos"
```

### Expected output (NOW WITH deleted_at):
```sql
CREATE TABLE todos (
	id INTEGER NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT, 
	is_completed BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL,
	deleted_at DATETIME, 
	PRIMARY KEY (id)
);
```

**🎉 Success! The `deleted_at` column was added!**

---

## Exercise 8: Check Migration Status

### Command 1: See what migration is currently applied
```bash
uv run alembic current
```

### Expected output:
```
abc1234def
```

This means: "Your database is at migration `abc1234def`. The `deleted_at` column exists."

### Command 2: See migration history
```bash
uv run alembic history
```

### Expected output:
```
abc1234def -> (head), add_deleted_at_column
```

This shows: `abc1234def` is the latest (head) migration, and it's named `add_deleted_at_column`.

---

## Exercise 9: Test Rollback (Downgrade)

Now let's test that we can rollback the migration. This is CRITICAL!

### Command:
```bash
uv run alembic downgrade -1
```

### Expected output:
```
INFO [alembic.runtime.migration] Context impl SQLiteImpl.
INFO [alembic.runtime.migration] Will assume non-transactional DDL.
INFO [alembic.runtime.migration] Running downgrade abc1234def -> , add_deleted_at_column
```

### Verify the rollback worked:
```bash
sqlite3 database.db ".schema todos"
```

### Expected output (deleted_at IS GONE):
```sql
CREATE TABLE todos (
	id INTEGER NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT, 
	is_completed BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id)
);
```

**The `deleted_at` column was removed!** Rollback works! ✅

---

## Exercise 10: Apply Migration Again (Verify Idempotency)

Let's apply the migration again to make sure it works twice (idempotent).

### Command:
```bash
uv run alembic upgrade head
```

### Expected output:
```
INFO [alembic.runtime.migration] Context impl SQLiteImpl.
INFO [alembic.runtime.migration] Will assume non-transactional DDL.
INFO [alembic.runtime.migration] Running upgrade  -> abc1234def, add_deleted_at_column
```

### Verify:
```bash
sqlite3 database.db ".schema todos"
```

Should show `deleted_at` column again. ✅

---

## Summary: What You've Learned

✅ **Initialize Alembic:** `alembic init alembic`
✅ **Configure env.py:** Import Base and set target_metadata
✅ **Create manual migration:** `alembic revision -m "description"`
✅ **Write upgrade() and downgrade():** Add/drop columns
✅ **Preview migration:** `alembic upgrade head --sql`
✅ **Apply migration:** `alembic upgrade head`
✅ **Check status:** `alembic current` and `alembic history`
✅ **Rollback:** `alembic downgrade -1`
✅ **Test idempotency:** Apply → Rollback → Apply again

---

## Quick Reference

```bash
# Setup
alembic init alembic                  # Initialize (first time only)
# (edit alembic/env.py)

# Create & Apply
alembic revision -m "description"     # Create empty migration
alembic upgrade head --sql            # Preview SQL (dry run)
alembic upgrade head                  # Apply migration

# Verify
alembic current                       # See current version
alembic history                       # See all migrations
sqlite3 database.db ".schema todos"   # Verify DB schema changed

# Rollback
alembic downgrade -1                  # Undo last migration
alembic downgrade base                # Undo all migrations

# Test
alembic upgrade head                  # Apply
alembic downgrade -1                  # Rollback
alembic upgrade head                  # Apply again (verify idempotency)
```

---

## What's Next?

Once you're comfortable with this workflow, we can:

1. **Auto-generate migrations** (faster): `alembic revision --autogenerate -m "msg"`
2. **Add soft delete to models.py** (add the deleted_at column to the Todo class)
3. **Let Alembic auto-generate the migration** (it'll compare models vs DB)
4. **Update CRUD functions** (filter out soft-deleted todos)
5. **Test the entire flow** together

Ready to proceed? 🚀
