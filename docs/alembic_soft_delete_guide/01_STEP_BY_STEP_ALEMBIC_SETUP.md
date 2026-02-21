# Alembic Setup & Migration: Step-by-Step Learning Guide

## Prerequisites Check
Before we start, verify you have alembic installed:

```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo
uv run alembic --version
```

You should see: `alembic, version 1.13.1` (or similar)

✅ Good! It's already in your `pyproject.toml` dependencies.

---

## Part 1: Understanding Alembic Structure

Before we initialize, let's understand what Alembic creates:

```
00_personal_todo/           ← Your project root
├── alembic.ini             ← Configuration file (database URL, etc)
└── alembic/                ← Alembic works in this directory
    ├── versions/           ← Each migration file goes here
    │   ├── 2026_02_21_001_initial.py      ← Migration 1: Creates initial tables
    │   ├── 2026_02_21_002_add_column.py   ← Migration 2: Adds a column
    │   └── 2026_02_22_001_rename_field.py ← Migration 3: Renames a field
    ├── env.py              ← HOW to connect to your database
    └── script.py.mako      ← Template for generating new migrations
```

**Key Concept**: Each migration file is like a Git commit, but for your database schema.

---

## Part 2: Step 1 - Initialize Alembic

### 2.1: Run the initialization command

```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo
uv run alembic init alembic
```

**What this does:**
- Creates the `alembic/` directory
- Generates `alembic/versions/` (where migrations go)
- Creates `alembic/env.py` (database connection config)
- Creates `alembic/script.py.mako` (migration template)
- Creates `alembic.ini` (main configuration)

**Expected output:**
```
Creating directory /home/db/Work/db_workshop/workshop/00_personal_todo/alembic ... done
Creating directory /home/db/Work/db_workshop/workshop/00_personal_todo/alembic/versions ... done
Generating /home/db/Work/db_workshop/workshop/00_personal_todo/alembic.ini ... done
Generating /home/db/Work/db_workshop/workshop/00_personal_todo/alembic/env.py ... done
```

After this, your project structure looks like:

```
00_personal_todo/
├── alembic/                ← NEW! Created by init
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── alembic.ini             ← NEW! Configuration
├── main.py
├── app/
│   ├── models.py
│   ├── schemas.py
│   ├── api/
│   │   └── todo_api.py
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   └── services/
│       └── todo_crud.py
├── database.db
└── ... (other files)
```

---

## Part 2: Step 2 - Understanding `alembic.ini`

This is Alembic's main configuration file. Let's look at the important part:

```bash
cat alembic.ini | grep -A 2 "sqlalchemy.url"
```

You'll see:
```ini
sqlalchemy.url = driver://user:password@localhost/dbname
```

**What this means:**
- This tells Alembic how to connect to your database
- Currently it's a placeholder (we'll configure it in `env.py` instead)

For SQLite, this would be:
```ini
sqlalchemy.url = sqlite:///./database.db
```

But we'll let Python (env.py) handle this, not the .ini file.

---

## Part 3: Step 3 - Understanding and Configuring `env.py`

This file is where the **magic** happens. It tells Alembic:
1. How to connect to your database
2. How to generate migrations
3. How to apply migrations

### 3.1: Open `alembic/env.py` and find this section:

```python
# alembic/env.py (around line 20-30)

from sqlalchemy import create_engine
from sqlalchemy import pool
from alembic import context

config = context.config
```

### 3.2: What needs to happen:

Alembic needs to know:
- ✅ What is your database URL? 
- ✅ What are your SQLAlchemy models?
- ✅ How to compare models vs database?

### 3.3: Configure env.py

We need to modify `env.py` to import from your project. Look for this line:

```python
target_metadata = None
```

**We need to change it to:**

```python
# Import your Base from your database module
from app.core.database import Base
target_metadata = Base.metadata
```

This tells Alembic: "Look at my SQLAlchemy models (in Base.metadata) to know what the schema should be."

### 3.4: Also configure the database URL

Find this function in `env.py`:

```python
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
```

**Change it to:**

```python
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    from app.core.database import engine
    url = engine.url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
```

And find:

```python
def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
```

**Change it to:**

```python
def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    from app.core.database import engine
    connectable = engine
```

---

## Part 4: Understanding Migration Files

Now that Alembic is configured, let's understand what a migration file looks like.

### 4.1: Simple Migration File Example

```python
# alembic/versions/001_add_deleted_at_column.py

"""Add deleted_at column to todos

This is the "description" - appears in history

Revision ID: abc1234def5678    ← Unique ID for this migration
Revises: None                   ← What migration came before? (None = first migration)
Create Date: 2024-02-19 10:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# These are metadata - Alembic tracks them
revision = 'abc1234def5678'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply this migration (move forward)."""
    op.add_column('todos', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Undo this migration (move backward)."""
    op.drop_column('todos', 'deleted_at')
```

### 4.2: Key Parts Explained

```python
# The two functions are CRITICAL:

def upgrade() -> None:
    """What to do when applying the migration (moving forward).
    
    Example: Add a column
    """
    op.add_column('todos', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """What to do when rolling back the migration (moving backward).
    
    Example: Remove the column
    """
    op.drop_column('todos', 'deleted_at')
```

**Think of it like:**
- `upgrade()` = Git commit (forward)
- `downgrade()` = Git revert (backward)

---

## Part 5: Two Ways to Create Migrations

There are two approaches:

### **Approach A: Auto-Generate (Easiest)**

Let Alembic compare your SQLAlchemy models vs the database:

```bash
uv run alembic revision --autogenerate -m "add soft delete to todos"
```

**How it works:**
1. Looks at your SQLAlchemy models (what SHOULD be there)
2. Looks at the database (what IS there)
3. Compares them
4. Auto-generates the migration code

**Pros**: Fast, automatic
**Cons**: Sometimes needs manual review

### **Approach B: Manual (Full Control)**

You write the migration code yourself:

```bash
uv run alembic revision -m "add soft delete to todos"
```

This creates an empty migration file where you write the `upgrade()` and `downgrade()` functions.

**Pros**: Full control, explicit
**Cons**: Slower, more work

---

## Part 6: How to Apply Migrations

Once you have a migration file, apply it:

```bash
# Apply ALL pending migrations
uv run alembic upgrade head

# Apply just 1 migration
uv run alembic upgrade +1

# Apply 3 migrations
uv run alembic upgrade +3

# Apply to a specific revision
uv run alembic upgrade abc1234def5678
```

**What "head" means:**
- `head` = the latest migration (the tip of your migration chain)
- `upgrade head` = apply everything up to the latest

---

## Part 7: How to Rollback Migrations

Undo migrations:

```bash
# Rollback the last migration
uv run alembic downgrade -1

# Rollback the last 3 migrations
uv run alembic downgrade -3

# Rollback ALL migrations (back to start)
uv run alembic downgrade base

# Rollback to a specific revision
uv run alembic downgrade abc1234def5678
```

**Why this matters:**
- Test your migrations: `upgrade head` → `downgrade -1` → `upgrade head`
- Verify they're reversible
- Catch bugs early

---

## Part 8: Checking Migration Status

### 8.1: See what's been applied

```bash
uv run alembic current
```

Output: Shows the current migration (what your database is at)

```
abc1234def5678
```

### 8.2: See all migrations (history)

```bash
uv run alembic history
```

Output: Shows all migrations in order

```
abc1234def5678 -> 2024-02-19 10:30:00 (head) -> Add deleted_at column
```

### 8.3: See what WILL happen (dry run)

```bash
uv run alembic upgrade head --sql
```

This shows the SQL that WOULD be executed, without actually running it. Great for preview!

---

## Part 9: Special Case - SQLite Batch Mode

**IMPORTANT**: SQLite has limitations with ALTER TABLE. When modifying columns, you MUST use "batch mode":

```python
# WRONG (doesn't work on SQLite):
def upgrade():
    op.add_column('todos', sa.Column('deleted_at', sa.DateTime(), nullable=True))

# RIGHT (works on SQLite):
def upgrade():
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))
```

Alembic's auto-generate usually does this correctly for SQLite, but good to know!

---

## Part 10: Migration Workflow (Step-by-Step)

Here's the exact workflow you'll follow every time you want to change the schema:

```
1. UPDATE MODELS
   └─→ models.py: Add new column or table

2. CREATE MIGRATION
   └─→ alembic revision --autogenerate -m "description"

3. REVIEW MIGRATION
   └─→ Open alembic/versions/xxx_description.py
   └─→ Verify upgrade() and downgrade() look correct

4. TEST LOCALLY
   └─→ alembic upgrade head
   └─→ alembic downgrade -1
   └─→ alembic upgrade head

5. VERIFY DATABASE CHANGED
   └─→ Query the database to confirm schema changed

6. COMMIT TO GIT
   └─→ git add alembic/versions/xxx_description.py
   └─→ git commit -m "feat: add column description"
```

---

## Part 11: Common Commands Cheat Sheet

| Goal | Command |
|------|---------|
| Initialize Alembic | `alembic init alembic` |
| Create auto-migration | `alembic revision --autogenerate -m "msg"` |
| Create manual migration | `alembic revision -m "msg"` |
| Apply all migrations | `alembic upgrade head` |
| Rollback 1 migration | `alembic downgrade -1` |
| See current version | `alembic current` |
| See migration history | `alembic history` |
| Preview SQL (dry run) | `alembic upgrade head --sql` |
| Edit latest migration | `alembic edit` |

---

## Part 12: Let's Do It Together!

Now you understand the theory. Let's actually set up Alembic for your project.

### Step 1: Initialize (we'll do this together)
```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo
uv run alembic init alembic
```

### Step 2: Configure env.py
We'll edit `alembic/env.py` to import your database and models.

### Step 3: Create a test migration
We'll create a simple migration to understand the process.

### Step 4: View migration history
We'll see what was created.

### Step 5: Test upgrade/downgrade
We'll apply and rollback the migration.

---

## Questions Before We Start?

Do you understand:
1. ✅ What Alembic is? (Version control for database)
2. ✅ The directory structure? (alembic/versions/ is where migrations live)
3. ✅ The difference between upgrade() and downgrade()? (forward/backward)
4. ✅ Auto-generate vs manual migrations? (auto compares models vs DB)
5. ✅ How to apply/rollback? (alembic upgrade head / alembic downgrade -1)

If yes, we're ready to implement! 🚀

Let's start by running the initialization command and then configuring `env.py`.
