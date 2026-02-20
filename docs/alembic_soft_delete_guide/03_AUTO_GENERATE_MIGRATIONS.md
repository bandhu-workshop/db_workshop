# Auto-Generate Migrations: The Faster Way

Once Alembic is set up, the easiest way to create migrations is to **let Alembic auto-generate them** from your model changes.

---

## How Auto-Generate Works

```
You change models.py
        ↓
Alembic reads your SQLAlchemy models
        ↓
Alembic reads your database schema
        ↓
Alembic compares them (what should be vs what is)
        ↓
Alembic auto-generates the migration code
        ↓
You review it, then apply it
```

---

## The Workflow: Auto-Generate vs Manual

| Step | Auto-Generate | Manual |
|------|---------------|--------|
| **Create migration** | `alembic revision --autogenerate -m "msg"` | `alembic revision -m "msg"` |
| **Write code** | Alembic does it | You write it |
| **Speed** | ⚡ Fast (seconds) | 🐢 Slow (minutes) |
| **Control** | Limited (you review) | Full control |
| **Common cases** | Add/drop columns, simple changes | Complex schema manipulation |

---

## Exercise: Auto-Generate a Migration

Let's add the `deleted_at` column using auto-generate (the industry-standard way).

### Step 1: First, undo the previous migration

Clear the database back to before we added `deleted_at`:

```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo
uv run alembic downgrade base
```

This reverts to the very beginning (before any migrations).

### Verify:
```bash
uv run alembic current
```

Expected output: (empty - no migrations applied)

And check the DB:
```bash
sqlite3 database.db ".schema todos"
```

Should NOT show `deleted_at` column.

---

### Step 2: Update `models.py` to add `deleted_at`

Edit your `models.py` file and add the `deleted_at` column to the `Todo` class:

**Find this in models.py:**
```python
class Todo(Base):
    __tablename__ = "todos"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # ADD THIS COLUMN:
```

**Add this:**
```python
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
```

**Full updated class:**
```python
class Todo(Base):
    """
    Model for a TODO with soft delete support.
    Note: The class name is singular (Todo) while the table name is plural (todos).
    """

    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
```

---

### Step 3: Create the migration (auto-generate)

Now tell Alembic to compare your updated models vs the database:

```bash
uv run alembic revision --autogenerate -m "add_soft_delete_to_todos"
```

### What happens:

Alembic:
1. Reads your `models.py` (sees `deleted_at` column)
2. Reads the database schema (doesn't see `deleted_at` column)
3. **Compares** them (finds the difference)
4. **Auto-generates** a migration file with the code to add `deleted_at`

### Expected output:
```
  Generating /home/db/Work/db_workshop/workshop/00_personal_todo/alembic/versions/xyz9999_add_soft_delete_to_todos.py ...  done
```

---

### Step 4: Review the auto-generated migration

```bash
ls -la alembic/versions/
```

You should see:
```
xyz9999_add_soft_delete_to_todos.py
```

Let's look at it:
```bash
cat alembic/versions/xyz9999_add_soft_delete_to_todos.py
```

### Expected content:

```python
"""add_soft_delete_to_todos

Revision ID: xyz9999
Revises: 
Create Date: 2024-02-19 10:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'xyz9999'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # For SQLite, Alembic automatically uses batch mode
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')
```

**🎯 Perfect! Alembic auto-generated everything for us!**

Key observations:
- ✅ `upgrade()` has `add_column('deleted_at', ...)`
- ✅ `downgrade()` has `drop_column('deleted_at')`
- ✅ SQLite batch mode is automatically used
- ✅ The column is `nullable=True` and `DateTime` type (matches our model)

---

### Step 5: Preview the migration (dry run)

Before applying, let's see the SQL:

```bash
uv run alembic upgrade head --sql
```

Expected output shows all the SQL that will be executed. Review it to make sure it looks correct.

---

### Step 6: Apply the migration

```bash
uv run alembic upgrade head
```

Expected output:
```
INFO [alembic.runtime.migration] Context impl SQLiteImpl.
INFO [alembic.runtime.migration] Will assume non-transactional DDL.
INFO [alembic.runtime.migration] Running upgrade  -> xyz9999, add_soft_delete_to_todos
```

---

### Step 7: Verify the change

Check the database schema:
```bash
sqlite3 database.db ".schema todos"
```

Should now show:
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

**✅ The `deleted_at` column was added!**

---

### Step 8: Test the migration (verify up/down/up)

A critical practice: test that your migration can be rolled back and re-applied.

```bash
# Test 1: Rollback
uv run alembic downgrade -1
sqlite3 database.db ".schema todos"   # Should NOT have deleted_at

# Test 2: Apply again
uv run alembic upgrade head
sqlite3 database.db ".schema todos"   # Should have deleted_at again

# Test 3: View history
uv run alembic history
uv run alembic current
```

✅ All three tests should pass!

---

## When to Use Auto-Generate vs Manual

### Use Auto-Generate When:
✅ Adding a column
✅ Dropping a column
✅ Creating a new table
✅ Adding an index
✅ Renaming a column (simple cases)
✅ Changing nullable/default (simple cases)

### Use Manual When:
✅ Complex schema changes (multiple coupled operations)
✅ Data transformations (e.g., split one column into two)
✅ Complex constraints
✅ You need precise control
✅ Data migration logic is involved

---

## Pro Tips for Auto-Generate

### Tip 1: Always review before applying

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Review it
cat alembic/versions/*.py

# Then apply
alembic upgrade head
```

Sometimes Alembic misses subtle changes or generates sub-optimal SQL.

### Tip 2: Make one change per migration

```
Good:
Migration 1: Add deleted_at column
Migration 2: Add is_archived column

Bad:
Migration 1: Add deleted_at AND is_archived AND rename field
```

This makes migrations easier to understand and roll back if needed.

### Tip 3: Test the downgrade path

```bash
alembic upgrade head        # Apply
alembic downgrade -1        # Rollback (verify it works)
alembic upgrade head        # Apply again (verify it's idempotent)
```

Never assume downgrade works if you haven't tested it!

### Tip 4: Always commit migration files to git

```bash
git add alembic/versions/xyz9999_description.py
git commit -m "chore: add migration for soft delete"
```

Migration files are source code now, not generated artifacts.

---

## Common Gotchas

### Gotcha 1: "No changes detected"
```bash
uv run alembic revision --autogenerate -m "..."
# Message: "No changes detected"
```

**Reason:** Alembic didn't see any differences between models and database.

**Solution:**
- Make sure you actually changed `models.py`
- Run `alembic current` to see what version the DB is at
- If DB is ahead of models, that's the problem

### Gotcha 2: "Invalid column name"
```
sqlalchemy.exc.OperationalError: no such column
```

**Reason:** Migration failed, database is in a broken state.

**Solution:**
1. Check what went wrong: `uv run alembic history`
2. Rollback: `uv run alembic downgrade -1` (or `-2`, etc.)
3. Fix the migration file
4. Delete the broken migration file from `alembic/versions/`
5. Create a new one

### Gotcha 3: SQLite locks up
```
database is locked
```

**Reason:** Another process is accessing the database.

**Solution:**
- Make sure your app isn't running
- Make sure no other terminals have the database open
- Close the database: `sqlite3 database.db "DELETE FROM alembic_version;"` (careful!)

---

## Workflow Summary

Here's what you'll do every time you want to change the schema:

```bash
# 1. Update models.py
# (Add new column, create new table, etc)

# 2. Create migration (Alembic auto-generates it!)
uv run alembic revision --autogenerate -m "description of change"

# 3. Review the generated file
cat alembic/versions/*.py

# 4. Preview the SQL (optional but recommended)
uv run alembic upgrade head --sql

# 5. Apply the migration
uv run alembic upgrade head

# 6. Test it (critical!)
uv run alembic downgrade -1
uv run alembic upgrade head

# 7. Verify the database changed
sqlite3 database.db ".schema table_name"

# 8. Commit to git
git add alembic/versions/
git commit -m "feat: add column description"
```

---

## Quick Command Reference

```bash
# Initialize (first time only)
alembic init alembic

# Create auto-generate migration
alembic revision --autogenerate -m "msg"

# Create manual migration
alembic revision -m "msg"

# Apply all pending migrations
alembic upgrade head

# Rollback 1 migration
alembic downgrade -1

# Rollback all
alembic downgrade base

# See current version
alembic current

# See history
alembic history

# Preview SQL (dry run)
alembic upgrade head --sql

# Check database schema
sqlite3 database.db ".schema table_name"
```

---

## You're Ready!

You now know:
✅ How auto-generate works
✅ When to use it vs manual migrations
✅ How to review generated code
✅ How to test migrations
✅ Pro tips and gotchas

The next step: Let's integrate this into your project with Makefile shortcuts! 🚀
