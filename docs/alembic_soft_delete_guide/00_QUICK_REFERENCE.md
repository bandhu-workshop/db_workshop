# Alembic Quick Reference Card

Print this or bookmark it! 📌

---

## 5-Minute Overview

**Alembic** = Version control for your database schema

```
Update models.py → Generate migration → Review → Apply → Test
```

---

## Setup (One-Time)

```bash
cd /home/db/Work/db_workshop/workshop/00_personal_todo

# 1. Initialize
uv run alembic init alembic

# 2. Edit alembic/env.py
# Add: from app.core.database import Base
# Change: target_metadata = Base.metadata

# 3. Done!
uv run alembic current  # Should work
```

---

## Standard Workflow (Every Change)

```bash
# 1. Edit models.py
# Add new column, table, etc.

# 2. Generate migration
uv run alembic revision --autogenerate -m "describe change"

# 3. Review
cat alembic/versions/*.py

# 4. Apply
uv run alembic upgrade head

# 5. Test
uv run alembic downgrade -1
uv run alembic upgrade head

# 6. Verify
sqlite3 database.db ".schema table_name"

# 7. Commit
git add alembic/versions/
git commit -m "feat: ..."
```

---

## With Makefile (Easier)

After adding targets to Makefile:

```bash
# Create migration (prompts for description)
make db-migrate

# Apply
make db-upgrade

# Rollback 1
make db-downgrade

# Check status
make db-status

# Test (up → down → up)
make db-test

# Reset to initial
make db-reset
```

---

## Quick Commands

| Task | Command |
|------|---------|
| Create migration | `uv run alembic revision --autogenerate -m "..."` |
| Apply | `uv run alembic upgrade head` |
| Rollback 1 | `uv run alembic downgrade -1` |
| Rollback all | `uv run alembic downgrade base` |
| Check version | `uv run alembic current` |
| Show history | `uv run alembic history` |
| Preview SQL | `uv run alembic upgrade head --sql` |

---

## Migration File Structure

```python
def upgrade() -> None:
    # What to do when applying (move forward)
    # Example: add a column
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
        )

def downgrade() -> None:
    # What to do when rolling back (move backward)
    # Opposite of upgrade()
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')
```

---

## Common Code Patterns

### Add Column
```python
def upgrade():
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('column_name', sa.DataType(), nullable=True)
        )

def downgrade():
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.drop_column('column_name')
```

### Drop Column
```python
def upgrade():
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.drop_column('column_name')

def downgrade():
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('column_name', sa.DataType(), nullable=True)
        )
```

### Rename Column
```python
def upgrade():
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.alter_column('old_name', new_column_name='new_name')

def downgrade():
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.alter_column('new_name', new_column_name='old_name')
```

### Create Table
```python
def upgrade():
    op.create_table(
        'new_table',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

def downgrade():
    op.drop_table('new_table')
```

---

## Important Rules

✅ **DO:**
- Create one migration per change
- Always write downgrade()
- Test: upgrade → downgrade → upgrade
- Review generated code
- Commit migration files to git
- Use `--autogenerate` for simple changes

❌ **DON'T:**
- Skip the downgrade path
- Edit migrations after applying
- Delete migration files
- Leave downgrade() as `pass`
- Skip to production without testing
- Modify database manually

---

## Soft Delete Example

```python
# 1. Update models.py
class Todo(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # ADD

# 2. Generate migration
uv run alembic revision --autogenerate -m "add soft delete"

# 3. Apply
uv run alembic upgrade head

# 4. Update CRUD
def get_todo(session, todo_id):
    todo = session.get(Todo, todo_id)
    if todo and todo.deleted_at is None:
        return todo
    return None

def delete_todo(session, todo_id):
    todo = session.get(Todo, todo_id)
    if todo:
        todo.deleted_at = datetime.utcnow()
        session.commit()
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "command not found" | Use `uv run alembic` |
| "No changes detected" | Did you edit models.py? |
| "Migration failed" | Rollback: `uv run alembic downgrade -1` |
| "Can't import Base" | Edit alembic/env.py |
| "Database locked" | Close other terminals accessing DB |

---

## File Locations

```
/home/db/Work/db_workshop/workshop/00_personal_todo/
├── alembic/                 ← Created by: alembic init
│   ├── versions/            ← Migration files go here
│   │   └── 2026_02_21_001_initial.py
│   └── env.py               ← Configure database connection
├── alembic.ini              ← Configuration
├── app/
│   ├── models.py            ← Your SQLAlchemy models
│   ├── schemas.py           ← Pydantic schemas
│   ├── api/
│   │   └── todo_api.py
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   └── services/
│       └── todo_crud.py
├── main.py                  ← Your FastAPI app
└── Makefile                 ← (Add db-* targets)
```

---

## Makefile Targets (Copy into Your Makefile)

```makefile
db-init:
	uv run alembic init alembic

db-migrate:
	@read -p "Enter description: " desc; uv run alembic revision --autogenerate -m "$$desc"

db-upgrade:
	uv run alembic upgrade head

db-downgrade:
	uv run alembic downgrade -1

db-status:
	@uv run alembic current && echo "" && uv run alembic history

db-test:
	uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

db-reset:
	uv run alembic downgrade base && uv run alembic upgrade head

.PHONY: db-init db-migrate db-upgrade db-downgrade db-status db-test db-reset
```

---

## Learning Path

1. Read: `01_STEP_BY_STEP_ALEMBIC_SETUP.md` (Theory)
2. Do: `02_HANDS_ON_EXERCISES.md` (Practice)
3. Learn: `03_AUTO_GENERATE_MIGRATIONS.md` (Industry Standard)
4. Apply: `04_COMPLETE_WORKFLOW_AND_MAKEFILE.md` (Professional)

---

## Remember

- **Alembic = Git for your database**
- **One migration = One change**
- **Always test downgrade**
- **Commit migration files**
- **upgrade() moves forward, downgrade() moves backward**

---

## Questions?

Refer to the detailed guides in:
`/home/db/Work/db_workshop/docs/alembic_soft_delete_guide/`

You have:
- `01_STEP_BY_STEP_ALEMBIC_SETUP.md` - Theory & concepts
- `02_HANDS_ON_EXERCISES.md` - Manual exercises
- `03_AUTO_GENERATE_MIGRATIONS.md` - Fast approach
- `04_COMPLETE_WORKFLOW_AND_MAKEFILE.md` - Professional workflow

---

Good luck! 🚀
