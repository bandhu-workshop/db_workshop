# Alembic Practical Scenarios: Delete, Test & Backup

## Scenario 1: Delete a Mistakenly Created Revision

### Situation
You accidentally ran:
```bash
alembic revision --autogenerate -m "wrong_migration"
```

Now there's an unwanted migration file in `alembic/versions/`. How do you remove it safely?

### The Solution (3 Steps)

#### Step 1: Check what you have

```bash
# See all migrations
uv run alembic history

# See current database version
uv run alembic current

# See if the migration was already applied
ls -la alembic/versions/
```

#### Step 2: Delete the migration file (2 cases)

**Case A: Migration was NOT applied to database yet**

If `alembic current` doesn't show your migration, it wasn't applied. Safe to delete:

```bash
# Simply delete the file
rm alembic/versions/2025_02_20_001_wrong_migration.py

# Verify it's gone
ls alembic/versions/
```

✅ **Done!** No database changes were made, so nothing to undo.

**Case B: Migration WAS already applied to database**

If `alembic current` shows your migration, it was applied. You need to undo it first:

```bash
# Step 1: Rollback the migration
uv run alembic downgrade -1

# Step 2: Verify it was rolled back
uv run alembic current

# Step 3: Now delete the file
rm alembic/versions/2025_02_20_001_wrong_migration.py

# Step 4: Verify
ls alembic/versions/
uv run alembic history
```

✅ **Done!** Database is back to previous state, file is deleted.

---

## Scenario 2: Test a Change Properly & Clean Up After

### Situation
You want to:
1. Add a column to a table
2. Test that it works
3. Clean it up and revert everything

### The Complete Workflow

#### Step 1: Make your change to models.py

```python
# models.py - ADD a new column temporarily for testing
class Todo(Base):
    __tablename__ = "todos"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # TEST COLUMN - you want to verify this works
    test_column = Column(String(100), nullable=True, default="test")
```

#### Step 2: Create the migration

```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo

uv run alembic revision --autogenerate -m "test_adding_column"
```

This creates: `alembic/versions/2025_02_20_001_test_adding_column.py`

#### Step 3: Review the migration file

```bash
cat alembic/versions/2025_02_20_001_test_adding_column.py
```

Verify it looks correct:
```python
def upgrade():
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('test_column', sa.String(length=100), nullable=True))

def downgrade():
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.drop_column('test_column')
```

#### Step 4: Apply the migration (TEST UPGRADE)

```bash
uv run alembic upgrade head
```

Expected output:
```
INFO [alembic.runtime.migration] Running upgrade  -> 2025_02_20_001_test_adding_column
```

#### Step 5: Verify it in the database

```bash
# Check the schema changed
sqlite3 database.db ".schema todos"
```

Should show `test_column` in the table. ✅

#### Step 6: Test your code (optional)

If you have CRUD functions to test:
```bash
make run  # Start your API server (in another terminal)

# In another terminal, test the endpoint
curl http://localhost:8080/todos
```

#### Step 7: Rollback (TEST DOWNGRADE)

Once you've verified it works, rollback:

```bash
uv run alembic downgrade -1
```

Expected output:
```
INFO [alembic.runtime.migration] Running downgrade 2025_02_20_001_test_adding_column -> 
```

#### Step 8: Verify the rollback

```bash
# Check the column is gone
sqlite3 database.db ".schema todos"

# Verify current version
uv run alembic current
```

Should NOT show `test_column`. ✅

#### Step 9: Revert your model change

Remove the test column from `models.py`:

```python
# models.py - REMOVE the test column
class Todo(Base):
    __tablename__ = "todos"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # test_column removed
```

#### Step 10: Delete the migration file

```bash
rm alembic/versions/2025_02_20_001_test_adding_column.py

# Verify
ls alembic/versions/
```

#### Step 11: Cleanup complete! ✅

Now everything is back to original:
- ❌ Migration file deleted
- ❌ Model change reverted
- ✅ Database unchanged
- ✅ Everything tested and verified

---

## Scenario 3: Local Database for Testing Migrations

### Situation
You want to:
1. Keep your main `database.db` untouched
2. Create a test database `database_test.db`
3. Test all migrations on test DB
4. Only apply to main DB when confident

### The Complete Solution

#### Step 1: Create a test database config

Create a new file: `core/database_test.py`

```python
# core/database_test.py
"""Test database configuration - separate from production"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use a different database file for testing
TEST_DATABASE_URL = "sqlite:///./database_test.db"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # Set to True for SQL debugging
)

# Create test SessionLocal
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def get_test_db():
    """Dependency to get a test database session"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_test_db():
    """Initialize test database with tables"""
    from core.database import Base
    Base.metadata.create_all(bind=test_engine)
```

#### Step 2: Update `alembic.ini` to support both databases

Edit `alembic.ini`:

```ini
sqlalchemy.url = 

# Add this section for test database
[test]
sqlalchemy.url = sqlite:///./database_test.db
```

#### Step 3: Create a Makefile target for test migrations

Add to your `Makefile`:

```makefile
# Test Database Migrations
db-test-init:
	@echo "Creating test database..."
	sqlite3 database_test.db ".databases"
	@echo "✅ Test database created"

db-test-migrate:
	@echo "Testing migrations on test database..."
	@read -p "Enter migration description: " desc; \
	ALEMBIC_ENV=test uv run alembic revision --autogenerate -m "$$desc"

db-test-upgrade:
	@echo "Applying migrations to TEST database..."
	ALEMBIC_ENV=test uv run alembic upgrade head
	@echo "✅ Test migrations applied"

db-test-downgrade:
	@echo "Rolling back TEST database..."
	ALEMBIC_ENV=test uv run alembic downgrade -1

db-test-status:
	@echo "Test database status:"
	@ALEMBIC_ENV=test uv run alembic current

db-test-reset:
	@echo "Resetting TEST database..."
	rm -f database_test.db
	@echo "✅ Test database reset"

db-test-copy-to-prod:
	@echo "⚠️  Copying test migrations to production..."
	@read -p "Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		uv run alembic upgrade head; \
		echo "✅ Production database updated"; \
	else \
		echo "❌ Cancelled"; \
	fi
```

#### Step 4: Alternative Simple Approach (Better for Learning)

Instead of environment variables, just use **separate commands**:

```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo

# Create test database
touch database_test.db

# Initialize it with current schema
sqlite3 database_test.db < <(sqlite3 database.db ".schema")

# Or use Python to copy:
python3 << 'EOF'
import shutil
shutil.copy('database.db', 'database_test.db')
print("✅ Test database created from main database")
EOF
```

#### Step 5: Test migrations on test database only

Create a Python script: `test_migrations.py`

```python
#!/usr/bin/env python3
"""
Test migrations on a separate database without affecting production.

Usage:
    python test_migrations.py
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

def test_migrations():
    """Test all migrations on a temporary database"""
    
    project_dir = Path(__file__).parent
    test_db = project_dir / "database_test.db"
    original_db = project_dir / "database.db"
    
    # Step 1: Create backup of test database
    print("📋 Setting up test database...")
    if test_db.exists():
        test_db.unlink()
    
    # Copy original to test
    shutil.copy(original_db, test_db)
    print(f"✅ Test database created from: {original_db}")
    
    # Step 2: Temporarily change working directory
    os.chdir(project_dir)
    
    # Step 3: Test upgrade
    print("\n🚀 Testing migration upgrade...")
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Upgrade failed:\n{result.stderr}")
        return False
    
    print("✅ Upgrade succeeded")
    print(result.stdout)
    
    # Step 4: Test downgrade
    print("\n🔄 Testing migration downgrade...")
    result = subprocess.run(
        ["uv", "run", "alembic", "downgrade", "-1"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Downgrade failed:\n{result.stderr}")
        return False
    
    print("✅ Downgrade succeeded")
    
    # Step 5: Test upgrade again
    print("\n🚀 Testing upgrade again (idempotency)...")
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Second upgrade failed:\n{result.stderr}")
        return False
    
    print("✅ Idempotency test passed")
    
    # Step 6: Cleanup
    print("\n🧹 Cleaning up test database...")
    test_db.unlink()
    print("✅ Test database cleaned up")
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("ALEMBIC MIGRATION TEST SUITE")
    print("=" * 50)
    
    success = test_migrations()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ ALL TESTS PASSED - Safe to apply to production!")
    else:
        print("❌ TESTS FAILED - Fix issues before production")
    print("=" * 50)
    
    exit(0 if success else 1)
```

Make it executable:
```bash
chmod +x test_migrations.py
```

Then run it:
```bash
python test_migrations.py
```

Expected output:
```
==================================================
ALEMBIC MIGRATION TEST SUITE
==================================================
📋 Setting up test database...
✅ Test database created from: database.db
🚀 Testing migration upgrade...
✅ Upgrade succeeded
🔄 Testing migration downgrade...
✅ Downgrade succeeded
🚀 Testing upgrade again (idempotency)...
✅ Idempotency test passed
🧹 Cleaning up test database...
✅ Test database cleaned up

==================================================
✅ ALL TESTS PASSED - Safe to apply to production!
==================================================
```

#### Step 6: The Workflow (Test → Verify → Apply)

```bash
# 1. Make your change to models.py

# 2. Create migration
uv run alembic revision --autogenerate -m "your_change"

# 3. Test it on test database (won't affect main database)
python test_migrations.py

# 4. If tests pass, apply to production
uv run alembic upgrade head

# Verify
sqlite3 database.db ".schema todos"
```

---

## Quick Reference: Three Scenarios

### Quick Ref 1: Delete Accidental Migration

```bash
# If NOT applied yet:
rm alembic/versions/2025_02_20_001_wrong.py

# If already applied:
uv run alembic downgrade -1
rm alembic/versions/2025_02_20_001_wrong.py

# Verify
uv run alembic history
uv run alembic current
```

### Quick Ref 2: Test & Cleanup

```bash
# 1. Make change to models.py

# 2. Create migration
uv run alembic revision --autogenerate -m "test"

# 3. Apply to test
uv run alembic upgrade head

# 4. Verify in DB
sqlite3 database.db ".schema table"

# 5. Rollback
uv run alembic downgrade -1

# 6. Revert models.py change

# 7. Delete migration
rm alembic/versions/2025_02_20_001_test.py
```

### Quick Ref 3: Test on Local DB

```bash
# 1. Create test database
cp database.db database_test.db

# 2. Use test_migrations.py script
python test_migrations.py

# 3. If successful, apply to main DB
uv run alembic upgrade head
```

---

## Safety Checklist

Before applying migrations to production:

- [ ] Migration file reviewed and correct
- [ ] `upgrade()` function looks good
- [ ] `downgrade()` function looks good
- [ ] Tested: `upgrade → downgrade → upgrade`
- [ ] Tested on separate database first
- [ ] No syntax errors
- [ ] All databases (test, staging, production) are backed up
- [ ] You have a rollback plan

---

## Common Scenarios & Solutions

| Scenario | Solution |
|----------|----------|
| Mistaken migration not applied | Delete file directly |
| Mistaken migration already applied | Downgrade, delete file |
| Want to test safely | Use test_migrations.py or database_test.db |
| Want to see impact | Use `alembic upgrade head --sql` |
| Need to rollback | Use `alembic downgrade -1` or `-N` |
| Multiple mistakes | Use `.downgrade base`, delete files, start over |

---

## Pro Tips

### Tip 1: Always use --sql to preview first
```bash
uv run alembic upgrade head --sql
# Review the SQL before applying!
```

### Tip 2: Keep database backups
```bash
# Before major migrations
cp database.db database.db.backup

# Later, if needed
cp database.db.backup database.db
```

### Tip 3: Use separate test DB for CI/CD
Your test database is perfect for:
- Automated tests
- CI/CD pipelines
- Testing multiple migrations in sequence
- Verifying rollback works

### Tip 4: Git-based approach
```bash
# Create branch for new migrations
git checkout -b feature/soft-delete

# Create and test migrations
alembic revision --autogenerate -m "soft delete"

# Test everything
python test_migrations.py

# Commit when confident
git commit -am "feat: add soft delete"

# Merge to main when approved
```

---

## Your Commands Quick Map

```bash
# Mistake Management
rm alembic/versions/file.py              # Delete unmigrated file
alembic downgrade -1 && rm file.py       # Delete migrated file

# Testing
alembic upgrade head --sql               # Preview without applying
python test_migrations.py                # Test full suite
alembic upgrade head -> downgrade -1     # Manual test up/down

# Local Database
cp database.db database_test.db          # Create test copy
python test_migrations.py                # Run all tests

# Safety
git checkout -b migration-branch         # Use branches for migrations
git commit alembic/versions/             # Track migration files
alembic history                          # See all migrations applied
```

You're now prepared for any Alembic scenario! 🚀
