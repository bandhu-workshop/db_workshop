# 02 — Applying Search to Our Todo Application

## What We're Implementing

Add **title keyword search** to the existing `GET /todos` list endpoint via
an optional `q` query parameter.

```
GET /todos?q=groceries
GET /todos?q=buy&page=1&limit=5
GET /todos              ← no q = return all (existing behaviour unchanged)
```

The response stays the same `PaginatedTodoResponse` shape — no new schema
needed.

---

## Architecture Map

```
API Layer  (todo_api.py)
  │  accepts:  q: str | None  (Query param)
  │  validates: strip, pass down
  ▼
CRUD Layer (todo_crud.py)
  │  adds:     .filter(Todo.title.ilike(f"%{q}%"))  when q is given
  │  returns:  (items, total_count)  — same as list_todos
  ▼
DB Layer   (SQLite via SQLAlchemy ORM)
  │  executes: SELECT … WHERE title LIKE '%groceries%' LIMIT 10 OFFSET 0
```

No new model, no new schema, no migration — purely a query filter addition.

---

## Step 1 — CRUD Layer (`todo_crud.py`)

We **extend** `list_todos` with an optional `q` parameter.

### Before

```python
def list_todos(
    session: Session,
    include_deleted: bool = False,
    page: int = 1,
    limit: int = 10,
) -> tuple[list[Todo], int]:
    query = session.query(Todo)
    if not include_deleted:
        query = query.filter(Todo.deleted_at.is_(None))

    total_count = query.count()
    items = (
        query.order_by(Todo.created_at.desc(), Todo.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return items, total_count
```

### After

```python
def list_todos(
    session: Session,
    include_deleted: bool = False,
    page: int = 1,
    limit: int = 10,
    q: str | None = None,           # ← new parameter
) -> tuple[list[Todo], int]:
    query = session.query(Todo)
    if not include_deleted:
        query = query.filter(Todo.deleted_at.is_(None))

    # title search — case-insensitive substring match
    if q:
        query = query.filter(Todo.title.ilike(f"%{q}%"))

    total_count = query.count()
    items = (
        query.order_by(Todo.created_at.desc(), Todo.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return items, total_count
```

### Key Points

- `ilike` = case-**i**nsensitive LIKE (SQLAlchemy cross-database method)
- In SQLite `LIKE` is already case-insensitive for ASCII, but using `ilike`
  makes intent explicit and the code portable to PostgreSQL without change.
- The filter is applied **before** `count()` so pagination totals are correct.
- Order of operations matters: **filter → count → paginate**.

---

## Step 2 — API Layer (`todo_api.py`)

We add `q` as a `Query` parameter to the existing `list_todos_endpoint` and
pass it to the CRUD function.

### Before

```python
@router.get("/", response_model=PaginatedTodoResponse, status_code=200)
def list_todos_endpoint(
    session: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number, starting from 1"),
    limit: int = Query(default=10, ge=1, le=20, description="Items per page (max 20)"),
):
    todos, total = list_todos(session, page=page, limit=limit)
    ...
```

### After

```python
@router.get("/", response_model=PaginatedTodoResponse, status_code=200)
def list_todos_endpoint(
    session: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number, starting from 1"),
    limit: int = Query(default=10, ge=1, le=20, description="Items per page (max 20)"),
    q: str | None = Query(           # ← new parameter
        default=None,
        min_length=1,
        max_length=100,
        description="Search todos by title keyword (case-insensitive).",
    ),
):
    todos, total = list_todos(session, page=page, limit=limit, q=q)
    ...
```

### Why `min_length=1`?

FastAPI validates this automatically. An empty string `q=` is different from
an absent `q` — we reject `q=` (length 0) rather than treating it as "no
filter", which could be confusing.

---

## The SQL That Gets Executed

When you call `GET /todos?q=buy&page=1&limit=10`:

```sql
-- count query (for pagination metadata)
SELECT count(*) AS count_1
FROM todos
WHERE todos.deleted_at IS NULL
  AND todos.title LIKE '%buy%' ESCAPE '\'

-- data query
SELECT todos.id, todos.title, todos.description,
       todos.is_completed, todos.created_at, todos.updated_at, todos.deleted_at
FROM todos
WHERE todos.deleted_at IS NULL
  AND todos.title LIKE '%buy%' ESCAPE '\'
ORDER BY todos.created_at DESC, todos.id DESC
LIMIT 10 OFFSET 0
```

---

## Example Requests & Responses

### Search for "grocery"

```
GET /todos?q=grocery
```

```json
{
  "data": [
    {
      "id": 3,
      "title": "Buy grocery items",
      "description": null,
      "is_completed": false,
      "created_at": "2026-02-22T10:00:00Z",
      "updated_at": null,
      "deleted_at": null
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total_items": 1,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

### No results

```
GET /todos?q=zzznomatch
```

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total_items": 0,
    "total_pages": 0,
    "has_next": false,
    "has_previous": false
  }
}
```

> Status is **200 OK** — an empty list is not an error.

---

## What We Did NOT Change

| Component        | Changed? | Reason                                      |
|------------------|----------|---------------------------------------------|
| `Todo` model     | No       | No new column needed                        |
| Database schema  | No       | No migration needed                         |
| `TodoResponse`   | No       | Response shape is identical                 |
| Other endpoints  | No       | Only `GET /todos` extended                  |

---

## Testing It Manually

Start the server:
```bash
make run
# or: uvicorn main:app --reload
```

Try in the browser or with curl:
```bash
# Search
curl "http://localhost:8000/todos?q=buy"

# Search with pagination
curl "http://localhost:8000/todos?q=buy&page=1&limit=5"

# No filter (existing behaviour)
curl "http://localhost:8000/todos"

# OpenAPI docs
open http://localhost:8000/docs
```

The `/docs` page will show the new `q` parameter with its description in the
`GET /todos` operation.

---

## Future Improvements (When You Need Them)

| Need                        | Solution                                              |
|-----------------------------|-------------------------------------------------------|
| Also search `description`   | `or_(Todo.title.ilike(...), Todo.description.ilike(...))` |
| Typo tolerance              | `pg_trgm` extension + GIN index                      |
| Search across many fields   | Full-text search (`tsvector`)                         |
| Very large dataset          | Elasticsearch / Typesense / Meilisearch               |
| Search result highlighting  | Return matched snippets from FTS `ts_headline()`      |

---

*Created: 2026-02-22*
