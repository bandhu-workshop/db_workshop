# How Pagination Applies to Your Todo Project

This document maps everything from the previous docs directly to your current codebase. No code will be changed here — this is the blueprint before implementation.

---

## 1. What Your Current Stack Looks Like

Your project follows a clean 3-layer architecture:

```
┌───────────────────────────────────────────────────────────────┐
│                        API Layer                              │
│   todo_api.py  →  defines routes, handles HTTP               │
├───────────────────────────────────────────────────────────────┤
│                       CRUD Layer                              │
│   todo_crud.py →  pure DB operations (returns ORM models)    │
├───────────────────────────────────────────────────────────────┤
│                       Schema Layer                            │
│   schemas.py   →  Pydantic models (request/response shapes)  │
├───────────────────────────────────────────────────────────────┤
│                       Model Layer                             │
│   models.py    →  SQLAlchemy ORM (the DB table definition)   │
└───────────────────────────────────────────────────────────────┘
```

Pagination touches **all four layers**. Let's walk through each one.

---

## 2. The Endpoint That Needs Pagination

Right now, this is your `list_todos` endpoint:

```python
# todo_api.py (current)

@router.get("/", response_model=list[TodoResponse], status_code=200)
def list_todos_endpoint(session: Session = Depends(get_db)):
    return list_todos(session)
```

And the CRUD function it calls:

```python
# todo_crud.py (current)

def list_todos(session: Session, include_deleted: bool = False) -> list[Todo]:
    query = session.query(Todo)
    if not include_deleted:
        query = query.filter(Todo.deleted_at.is_(None))
    return query.all()   # ← returns EVERYTHING
```

This is what we need to transform.

---

## 3. Layer-by-Layer: What Changes and Why

### Layer 1 — Schemas (`schemas.py`)

Currently `TodoResponse` represents a single todo item. For pagination you need two new schemas:

**A. `TodoPaginationParams`** — captures what the client sends in the query string:

```python
# What the CLIENT sends:
GET /todos?page=2&limit=10
```

This needs to be a Pydantic schema (or FastAPI `Query` params) with validation:
- `page: int` — must be >= 1, defaults to 1
- `limit: int` — must be >= 1 and <= 100, defaults to 10

**B. `PaginatedTodoResponse`** — the new response envelope:

```python
# What the SERVER returns:
{
  "data": [ {...}, {...}, ... ],          # list of TodoResponse
  "pagination": {
    "page": 2,
    "limit": 10,
    "total_items": 47,
    "total_pages": 5,
    "has_next": true,
    "has_previous": true
  }
}
```

This means **the response type of the endpoint changes** from `list[TodoResponse]` to `PaginatedTodoResponse`.

---

### Layer 2 — CRUD (`todo_crud.py`)

The CRUD function needs to change its signature and return type. Instead of:

```python
def list_todos(session, include_deleted) -> list[Todo]:
    ...
    return query.all()
```

It needs to accept pagination parameters and return two things:
- The slice of todos for this page
- The total count

**Conceptually** it will run two queries:

```sql
-- Query 1: Get the count (for metadata)
SELECT COUNT(*) FROM todos WHERE deleted_at IS NULL;
-- → e.g. 47

-- Query 2: Get the actual page of data
SELECT * FROM todos WHERE deleted_at IS NULL
ORDER BY created_at DESC, id DESC
LIMIT 10 OFFSET 10;
-- → 10 rows (page 2)
```

**Why two queries?** Because `.count()` and `.all()` are different operations. You cannot get "how many total rows exist" from a query that only returns 10 rows.

**What the function might return:** A tuple `(todos: list[Todo], total: int)` or a dedicated result object. The API layer then uses the total count to build the `pagination` metadata.

---

### Layer 3 — API (`todo_api.py`)

The route function gains two new query parameters and changes its response model:

```python
# Conceptually (not final code):

@router.get("/", response_model=PaginatedTodoResponse, status_code=200)
def list_todos_endpoint(
    page: int = 1,          # ← new
    limit: int = 10,        # ← new
    session: Session = Depends(get_db),
):
    todos, total = list_todos(session, page=page, limit=limit)

    total_pages = math.ceil(total / limit)

    return PaginatedTodoResponse(
        data=todos,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )
    )
```

The API layer is now responsible for computing the metadata — it is the correct place because:
- CRUD handles DB. It should return raw data + count.
- API handles HTTP responses. It should shape the response envelope.
- Schemas handle validation. They should enforce constraints on `page` and `limit`.

---

### Layer 4 — Model (`models.py`)

Your `Todo` model in `models.py` does **not need to change**. The model defines the database table, and pagination is handled entirely in the query layer above.

---

## 4. The Request/Response Lifecycle

Here is what happens end-to-end when a client calls `GET /todos?page=2&limit=5`:

```
Client
  │
  │  GET /todos?page=2&limit=5
  ▼
API Layer (todo_api.py)
  │  1. FastAPI parses page=2, limit=5 from query string
  │  2. FastAPI validates: page >= 1? limit between 1 and 100?
  │  3. Calls list_todos(session, page=2, limit=5)
  ▼
CRUD Layer (todo_crud.py)
  │  4. Computes offset = (2 - 1) * 5 = 5
  │  5. Runs COUNT(*) query → returns 47
  │  6. Runs SELECT ... LIMIT 5 OFFSET 5 → returns 5 Todo ORM objects
  │  7. Returns (todos=[...5 items...], total=47)
  ▼
API Layer (todo_api.py)
  │  8. Computes total_pages = ceil(47 / 5) = 10
  │  9. Computes has_next = 2 < 10 → True
  │  10. Computes has_previous = 2 > 1 → True
  │  11. Builds PaginatedTodoResponse
  ▼
Client
     Receives:
     {
       "data": [ 5 todo items ],
       "pagination": {
         "page": 2,
         "limit": 5,
         "total_items": 47,
         "total_pages": 10,
         "has_next": true,
         "has_previous": true
       }
     }
```

---

## 5. Files That Will Change

| File | Change Needed |
|---|---|
| `app/schemas.py` | Add `PaginationMeta` and `PaginatedTodoResponse` schemas |
| `app/services/todo_crud.py` | Update `list_todos()` to accept `page`/`limit`, return `(todos, total)` |
| `app/api/todo_api.py` | Add `page`/`limit` query params, update response model, build envelope |
| `app/models.py` | **No change needed** |
| `app/core/` | **No change needed** |

---

## 6. Edge Cases to Anticipate

Before implementation, think through these scenarios:

### Empty database

- `total_items = 0`, `total_pages = 0` (or `1`? — industry uses `0`)
- `has_next = False`, `has_previous = False`
- `data = []`
- Status code: `200 OK` (not `404`)

### Client requests a page beyond the last page

```
GET /todos?page=999&limit=10
(but only 47 todos exist → only 5 pages)
```

Two valid approaches:
1. Return `200 OK` with `data: []` and correct metadata — simple, no error
2. Return `404` — explicit error

**Industry preference:** Return `200` with empty data. Clients handle "no more items" gracefully. `404` is for resources that don't exist, not for empty sets.

### Client sends `limit=0` or `page=0`

Pydantic validators (`ge=1`) will automatically reject these and return `422 Unprocessable Entity` before the code even runs.

### Client sends `limit=99999`

Server-side cap: `actual_limit = min(limit, MAX_LIMIT)` where `MAX_LIMIT = 100`.

---

## 7. How the Swagger UI Will Look After Implementation

FastAPI auto-generates interactive docs. After adding pagination, hitting `/docs` will show:

```
GET /todos

Parameters:
  page   (query)  integer  default: 1   minimum: 1
  limit  (query)  integer  default: 10  minimum: 1  maximum: 100

Response 200:
  {
    "data": [ TodoResponse, ... ],
    "pagination": {
      "page": integer,
      "limit": integer,
      "total_items": integer,
      "total_pages": integer,
      "has_next": boolean,
      "has_previous": boolean
    }
  }
```

This is significantly more informative than the current `list[TodoResponse]`.

---

## 8. What About the Other List Endpoints?

You have two other list-style endpoints:

```python
# get all completed todos
GET /todos/completed   → get_all_completed_todo()
```

This endpoint should also be paginated following the same pattern. The only difference is the filter: `is_completed == True`.

For the purpose of learning, we will start with `GET /todos` (the `list_todos` endpoint) and then apply the same pattern to `GET /todos/completed`.

---

## 9. The Sorting Decision

Your current queries have no explicit `ORDER BY`. This is undefined behavior — the database can return rows in any order. Before or during pagination implementation, add a consistent sort:

```python
# Recommended: newest first, id as tiebreaker
ORDER BY created_at DESC, id DESC
```

Why newest first?
- In a todo list, recent items are most relevant
- It matches what users expect from most list-based UIs
- Consistent with how GitHub Issues, Notion, etc. behave

---

## 10. Summary

```
What changes:
┌─────────────────────────────────────────────────────────────┐
│ schemas.py    → 2 new schemas: PaginationMeta,              │
│                               PaginatedTodoResponse         │
├─────────────────────────────────────────────────────────────┤
│ todo_crud.py  → list_todos() accepts page + limit,          │
│                 runs COUNT + SELECT, returns (todos, total)  │
├─────────────────────────────────────────────────────────────┤
│ todo_api.py   → route accepts page/limit query params,      │
│                 builds the response envelope                 │
└─────────────────────────────────────────────────────────────┘

What stays the same:
┌─────────────────────────────────────────────────────────────┐
│ models.py     → untouched                                   │
│ core/         → untouched                                   │
│ All other endpoints → untouched                             │
└─────────────────────────────────────────────────────────────┘
```

---

> Prev: [02_BEST_PRACTICES.md](./02_BEST_PRACTICES.md)  
> Back to index: [README.md](./README.md)

---
*Created: 2026-02-21*
