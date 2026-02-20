# Quick Action Plan: Resolve UNIQUE Constraint Mismatch

## What's Wrong

Your SQLAlchemy models no longer define a UNIQUE constraint on `todos.title`, but your SQLite database still enforces it. This is **database schema drift**.

## Immediate Fix (Choose One)

### ✅ Option 1: Clean Slate (development-only, no data loss acceptable)
```python
# Run this in Python:
from workshop.personal_TODO.database import engine
from workshop.personal_TODO.models import Base

# Delete all tables
Base.metadata.drop_all(bind=engine)

# Recreate from current models (constraint-free)
Base.metadata.create_all(bind=engine)
```
- **Time**: 5 minutes
- **Risk**: Low (dev environment)
- **Data**: Lost (acceptable in dev)

### ✅ Option 2: Delete Database File (easiest)
```bash
# Remove SQLite database file
rm -f workshop/00_personal_TODO/todos.db
# Or wherever your database file is located

# Restart your app - it will auto-create fresh schema
```
- **Time**: 1 minute
- **Risk**: Very low
- **Data**: Lost

### ⚠️ Option 3: Manual SQL (preserves data if any)
Use a SQL client to execute the constraint removal script documented in `DATABASE_SCHEMA_MIGRATION.md`
- **Time**: 10 minutes
- **Risk**: Medium (SQLite quirks)
- **Data**: Preserved

## Verify Fix

After applying any fix, verify the constraint is gone:

```bash
# Using sqlite3 CLI
sqlite3 workshop/00_personal_TODO/todos.db ".schema todos"

# Should show: title VARCHAR(255) NOT NULL
# Should NOT show: UNIQUE keyword
```

## Test It

```bash
# Create first todo with "Buy Milk"
curl -X POST http://localhost:8000/todos/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy Milk", "description": "morning"}'

# Create second todo with same title (idempotency test)
curl -X POST http://localhost:8000/todos/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy Milk", "description": "morning"}'

# ✅ Both should succeed and create different IDs
# ❌ If second fails with IntegrityError, constraint still exists
```

## Prevent Future Issues

### 1. Review Your Models
Ensure all UNIQUE constraints are intentional:
```python
# ❌ Bad: Creates implicit constraint
title = Column(String(255), unique=True)

# ✅ Good: Explicit documentation of why it's unique
title = Column(String(255), nullable=False)  # Allow duplicates for idempotency
```

### 2. Set Up Alembic (Long-term)
When ready to stop using SQLite `create_all()` magic:
```bash
alembic init alembic
# This enables version-controlled migrations for all databases
```

### 3. Document Decision
Add comment to `models.py`:
```python
class Todo(Base):
    """
    TODO model with idempotent creation support.
    
    Note: No UNIQUE constraint on title to support idempotent POST requests.
    Duplicate titles are allowed; use idempotency_key pattern for true idempotency.
    See: DATABASE_SCHEMA_MIGRATION.md
    """
```

## Understanding Idempotency

**Current State**: 
- Removing UNIQUE constraint allows duplicate titles
- BUT different resource created each time (not truly idempotent)

**True Idempotency** requires an **idempotency key** (see DATABASE_SCHEMA_MIGRATION.md for details):
- Same request always returns same resource (or existing one)
- Safe to retry without side effects
- Better user experience for flaky networks

## Decision Tree

```
Do you have important data? 
├─ No  → Use Option 2 (delete DB file) [5 seconds]
└─ Yes → Use Option 3 (manual SQL) [10 minutes] 
         Then set up Alembic to prevent recurrence [30 minutes]

Ready for production?
└─ Later → Set up Alembic + Migrations [1 hour one-time investment]
```

## Files to Review

1. **DATABASE_SCHEMA_MIGRATION.md** - Full analysis and long-term strategies
2. **[models.py]** - Verify no UNIQUE constraints remain
3. **[todo_crud.py]** - Ensure create_todo accepts duplicates

---

**Status**: After fix, your database will align with code. Next: Implement true idempotency with idempotency keys (optional, but recommended for production).

