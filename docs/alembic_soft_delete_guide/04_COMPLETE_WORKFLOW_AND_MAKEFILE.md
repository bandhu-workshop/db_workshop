# Complete Alembic Workflow: Summary & Makefile Integration

This is your **complete reference guide** that ties everything together.

---

## The Big Picture

```
Your Code Changes
       ↓
Models Updated (add/drop columns)
       ↓
Generate Migration (Alembic auto or manual)
       ↓
Review Migration File (.py in alembic/versions/)
       ↓
Test: Upgrade → Downgrade → Upgrade
       ↓
Apply Migration (alembic upgrade head)
       ↓
Database Schema Updated
       ↓
Commit to Git (git add alembic/versions/)
```

---

## The Complete Workflow (Step-by-Step)

### Phase 1: One-Time Setup

```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo

# Step 1: Initialize Alembic
uv run alembic init alembic

# Step 2: Configure alembic/env.py
# (Edit file to import Base and set target_metadata)

# Step 3: Verify it works
uv run alembic current
```

### Phase 2: Every Time You Change Schema

```bash
# Step 1: Change your models.py
# (Add new column, create new table, etc)

# Step 2: Create migration (auto-generate)
uv run alembic revision --autogenerate -m "describe the change"

# Step 3: Review alembic/versions/xxx_describe.py

# Step 4: Preview the SQL (optional)
uv run alembic upgrade head --sql

# Step 5: Apply the migration
uv run alembic upgrade head

# Step 6: Test it
uv run alembic downgrade -1
uv run alembic upgrade head

# Step 7: Verify database changed
sqlite3 database.db ".schema table_name"

# Step 8: Commit to git
git add alembic/versions/
git commit -m "feat: add soft delete to todos"
```

---

## Makefile Integration (Professional Workflow)

Add these targets to your `Makefile` in `/home/db/Work/db_workshop/workshop/00_personal_todo/Makefile`:

### Option 1: Simple Targets (Recommended for Learning)

```makefile
# Database Migrations - Simple targets
db-init:
	@echo "Initializing Alembic..."
	uv run alembic init alembic
	@echo "✅ Alembic initialized"
	@echo "Next: Configure alembic/env.py, then run: make db-status"

db-migrate:
	@echo "Creating migration..."
	@read -p "Enter migration description: " desc; \
	uv run alembic revision --autogenerate -m "$$desc"

db-upgrade:
	@echo "Applying migrations..."
	uv run alembic upgrade head
	@echo "✅ Migrations applied"

db-downgrade:
	@echo "Rolling back last migration..."
	uv run alembic downgrade -1
	@echo "✅ Migration rolled back"

db-status:
	@echo "Current database version:"
	uv run alembic current
	@echo ""
	@echo "Migration history:"
	uv run alembic history

db-test:
	@echo "Testing migrations (up → down → up)..."
	uv run alembic upgrade head
	uv run alembic downgrade -1
	uv run alembic upgrade head
	@echo "✅ Migration test passed"

db-reset:
	@echo "⚠️  WARNING: Resetting database to initial state!"
	uv run alembic downgrade base
	uv run alembic upgrade head
	@echo "✅ Database reset complete"

.PHONY: db-init db-migrate db-upgrade db-downgrade db-status db-test db-reset
```

### Option 2: Enhanced Targets (Professional)

```makefile
# Database Migrations - Enhanced targets
db-init:
	@echo "Initializing Alembic..."
	@if [ -d alembic ]; then \
		echo "❌ Alembic already initialized"; \
	else \
		uv run alembic init alembic; \
		echo "✅ Alembic initialized"; \
		echo "Next: Configure alembic/env.py"; \
	fi

db-migrate:
	@echo "Creating auto-migration..."
	@read -p "Enter migration description: " desc; \
	uv run alembic revision --autogenerate -m "$$desc"; \
	echo "✅ Migration created in alembic/versions/"; \
	echo "Review the file, then run: make db-upgrade"

db-show:
	@echo "Migration generated SQL (preview):"
	uv run alembic upgrade head --sql

db-upgrade:
	@echo "Applying migrations to database..."
	uv run alembic upgrade head
	@echo "✅ Migrations applied"
	@make db-status

db-downgrade:
	@echo "Rolling back last migration..."
	uv run alembic downgrade -1
	@echo "✅ Migration rolled back"

db-status:
	@echo "📊 Current database version:"
	uv run alembic current
	@echo ""
	@echo "📜 Migration history:"
	uv run alembic history

db-history:
	uv run alembic history --verbose

db-test:
	@echo "🧪 Testing migrations (upgrade → downgrade → upgrade)..."
	@echo "Step 1: Apply all migrations..."
	uv run alembic upgrade head
	@echo "Step 2: Rollback last migration..."
	uv run alembic downgrade -1
	@echo "Step 3: Apply again (verify idempotency)..."
	uv run alembic upgrade head
	@echo "✅ Migration test PASSED!"

db-reset:
	@echo "⚠️  WARNING: Resetting database to INITIAL STATE!"
	@read -p "Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		uv run alembic downgrade base; \
		uv run alembic upgrade head; \
		echo "✅ Database reset complete"; \
	else \
		echo "❌ Reset cancelled"; \
	fi

db-current:
	uv run alembic current

db-clean:
	@echo "Removing alembic directory and migration history..."
	rm -rf alembic/ alembic.ini
	@echo "✅ Alembic cleaned"

.PHONY: db-init db-migrate db-show db-upgrade db-downgrade db-status db-history db-test db-reset db-current db-clean
```

---

## Your Updated Makefile (Complete)

Here's what your full `Makefile` should look like:

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
	@echo "✅ Alembic initialized"
	@echo "Next: Edit alembic/env.py, then run: make db-migrate"

db-migrate:
	@echo "Creating auto-migration..."
	@read -p "Enter migration description: " desc; \
	uv run alembic revision --autogenerate -m "$$desc"
	@echo "✅ Review alembic/versions/, then run: make db-upgrade"

db-show:
	@echo "Preview: SQL that will be executed"
	uv run alembic upgrade head --sql

db-upgrade:
	@echo "Applying all pending migrations..."
	uv run alembic upgrade head
	@echo "✅ Done. Run 'make db-status' to verify"

db-downgrade:
	@echo "Rolling back last migration..."
	uv run alembic downgrade -1

db-status:
	@echo "Current database version:"
	@uv run alembic current
	@echo ""
	@echo "Migration history:"
	@uv run alembic history

db-test:
	@echo "Testing migrations: upgrade → downgrade → upgrade..."
	uv run alembic upgrade head
	uv run alembic downgrade -1
	uv run alembic upgrade head
	@echo "✅ Migration test PASSED"

db-reset:
	@echo "⚠️  Resetting database to initial state..."
	uv run alembic downgrade base
	uv run alembic upgrade head
	@echo "✅ Reset complete"

.PHONY: check_format check_type format run db-init db-migrate db-show db-upgrade db-downgrade db-status db-test db-reset
```

---

## Quick Reference: Common Tasks

### Task 1: Initialize Alembic (First Time)

```bash
make db-init
```

Then edit `alembic/env.py` to import Base.

### Task 2: Add a Column to a Table

```bash
# 1. Edit models.py and add the column
# 2. Generate migration
make db-migrate
# (Enter description, e.g., "add deleted_at to todos")

# 3. Review the generated file
cat alembic/versions/*deleted_at*.py

# 4. Apply migration
make db-upgrade

# 5. Test it
make db-test
```

### Task 3: See Migration Status

```bash
make db-status
```

Shows current version and migration history.

### Task 4: Rollback All Changes

```bash
make db-reset
```

Reverts database to initial state, then re-applies all migrations.

### Task 5: Rollback Just One Migration

```bash
make db-downgrade
```

Undo the last migration.

---

## All Makefile Commands

| Command | What It Does |
|---------|--------------|
| `make db-init` | Initialize Alembic (run once) |
| `make db-migrate` | Create auto-migration from model changes |
| `make db-show` | Preview SQL that will be executed |
| `make db-upgrade` | Apply all pending migrations |
| `make db-downgrade` | Rollback last migration |
| `make db-status` | Show current version and history |
| `make db-test` | Test migrations (up → down → up) |
| `make db-reset` | Reset database to initial state |

---

## Advanced Alembic Commands (If Needed)

```bash
# Edit the latest migration
uv run alembic edit

# Stamp the database (mark as if migration applied - use with caution!)
uv run alembic stamp head

# Create a branch in migrations
uv run alembic branches

# Merge migration branches
uv run alembic merge --branch-label=migration_xyz

# Detailed history
uv run alembic history --verbose

# Downgrade to specific revision
uv run alembic downgrade abc1234def5678
```

---

## Soft Delete Example (The Real Use Case)

Once you're comfortable with the workflow, here's how to add soft delete:

### Step 1: Update models.py

```python
from sqlalchemy import DateTime

class Todo(Base):
    __tablename__ = "todos"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # ADD THIS:
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
```

### Step 2: Create migration

```bash
make db-migrate
# Enter: "add soft delete to todos"
```

### Step 3: Review generated migration

```bash
cat alembic/versions/*soft_delete*.py
```

Should show `upgrade()` with `add_column('deleted_at', ...)`

### Step 4: Apply migration

```bash
make db-upgrade
```

### Step 5: Update CRUD to filter soft-deleted rows

```python
def get_todo(session, todo_id):
    todo = session.get(Todo, todo_id)
    # Only return if NOT soft-deleted
    if todo and todo.deleted_at is None:
        return todo
    return None

def delete_todo(session, todo_id):
    todo = session.get(Todo, todo_id)
    if todo:
        todo.deleted_at = datetime.utcnow()  # Soft delete
        session.commit()
    return True
```

### Step 6: Done!

You've implemented soft delete with migrations! 🎉

---

## Checklist: Before You Write Code

- [ ] Alembic is initialized (`make db-init`)
- [ ] `alembic/env.py` is configured (imports Base)
- [ ] You understand: upgrade = forward, downgrade = rollback
- [ ] You know how to: generate → review → test → apply
- [ ] Makefile targets are added
- [ ] Git is tracking `alembic/versions/`

---

## What NOT to Do

❌ Don't manually edit the database schema without a migration
❌ Don't commit changes without testing migrations
❌ Don't modify migration files after they've been applied
❌ Don't skip the downgrade path
❌ Don't delete migration files
❌ Don't run migrations in parallel

---

## Troubleshooting

### Problem: "alembic: command not found"
```bash
# Solution: use uv run
uv run alembic --version
```

### Problem: "env.py can't import Base"
```bash
# Solution: Edit alembic/env.py
# Make sure: from core.database import Base
```

### Problem: "No changes detected"
```bash
# Solution: Did you actually edit models.py?
# Check: git diff models.py
```

### Problem: Migration fails
```bash
# Solution: Rollback
uv run alembic downgrade -1

# Delete the bad migration
rm alembic/versions/bad_migration.py

# Create it again
make db-migrate
```

---

## Next Steps

1. ✅ **Understand the theory** - Read the learning guides
2. ✅ **Set up Alembic** - Run `make db-init`
3. ✅ **Configure env.py** - Edit alembic/env.py
4. ✅ **Add Makefile targets** - Copy the Makefile code above
5. ✅ **Test the workflow** - Create a test migration
6. ✅ **Add soft delete to models** - Add `deleted_at` column
7. ✅ **Auto-generate migration** - Run `make db-migrate`
8. ✅ **Update CRUD** - Filter soft-deleted rows
9. ✅ **Test everything** - Run `make db-test`
10. ✅ **Commit to git** - `git add alembic/` && `git commit`

---

## You're Ready!

You now have:
✅ Complete understanding of Alembic
✅ Hands-on experience with migrations
✅ Makefile shortcuts for easy workflow
✅ Clear examples and best practices
✅ Troubleshooting guide

**Next:** Let's implement soft delete together using this knowledge! 🚀
