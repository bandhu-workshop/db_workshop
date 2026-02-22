# 01 — Search: Best Practices & Industry Standards

## API Design

### Use a query parameter, not a separate endpoint

```
✅ GET /todos?q=buy              (extend the list endpoint)
❌ GET /todos/search?q=buy       (unnecessary separate endpoint)
❌ POST /todos/search  { "q": "buy" }  (search is a READ — never POST)
```

The `q` (or `query`) query parameter is the universal REST convention —
used by Google, GitHub, Stripe, and virtually every public API.

### Combine search with pagination

Search results can be large. Always paginate them:

```
GET /todos?q=groceries&page=1&limit=10
```

The same `PaginatedTodoResponse` you use for listing applies to search.

### Combine search with other filters

Search should compose freely with existing filters:

```
GET /todos?q=buy&include_deleted=false&page=2&limit=10
```

This means: add `q` as an additional optional parameter to the **existing
list endpoint** rather than duplicating all filter logic in a new endpoint.

---

## Parameter Naming Conventions

| Name      | Used by             | Notes                                 |
|-----------|---------------------|---------------------------------------|
| `q`       | Google, GitHub, ES  | Most universal, shortest              |
| `query`   | Elasticsearch API   | Explicit, good for domain APIs        |
| `search`  | Some internal APIs  | Clear but verbose                     |
| `keyword` | Less common         | Avoid — misleadingly narrow           |
| `filter`  | OData               | For structured filters, not free text |

**Recommendation:** use `q` for public/user-facing APIs, `query` for internal
service-to-service APIs.

---

## Input Sanitisation

### Always strip whitespace

```python
q = q.strip() if q else None
```

A query of `"  buy  "` should behave identically to `"buy"`.

### Minimum length guard (optional but recommended)

```python
if q and len(q) < 2:
    raise HTTPException(422, "Search query must be at least 2 characters")
```

Avoids accidental "search for everything" broadness (e.g., `q=a`).

### Never interpolate raw input into SQL

```python
# ❌ SQL injection risk
session.execute(f"SELECT * FROM todos WHERE title LIKE '%{q}%'")

# ✅ Parameterised (SQLAlchemy does this automatically with .ilike())
query.filter(Todo.title.ilike(f"%{q}%"))
```

SQLAlchemy's ORM methods are **always parameterised** — safe by default.

---

## Returning "No Results" vs "Error"

| Situation           | HTTP Status | Body                                         |
|---------------------|-------------|----------------------------------------------|
| Search returns 0    | `200 OK`    | `{ "data": [], "pagination": { … } }`        |
| Missing `q` param   | `200 OK`    | Return all results (treat as absent filter)  |
| `q` too short       | `422`       | Validation error (optional policy)           |
| DB error            | `500`       | Internal server error                        |

**Never return 404 for empty search results.** An empty list is a valid,
successful response.

---

## Performance Checklist

| Scale          | Technique                                              |
|----------------|--------------------------------------------------------|
| < 50k rows     | `LIKE '%q%'` — acceptable                             |
| 50k–500k rows  | Add trigram GIN index (`pg_trgm`)                     |
| > 500k rows    | Full-text search (`tsvector`) or dedicated search engine |
| Millions+      | Elasticsearch / OpenSearch / Typesense / Meilisearch  |

### Index your search column

```sql
-- For LIKE with trailing wildcard only (e.g., 'buy%')
CREATE INDEX idx_todos_title ON todos (title);

-- For LIKE with leading wildcard ('%buy%') — requires pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_todos_title_trgm ON todos USING GIN (title gin_trgm_ops);
```

For SQLite in this workshop, the dataset is tiny — no index needed yet.

---

## Caching Considerations

For high-traffic search endpoints:

1. **Cache at the application layer** (Redis, in-memory) keyed by `(q, page, limit)`.
2. **Cache TTL**: 30–60 seconds for near-real-time data; longer for static data.
3. **Invalidate on write**: clear relevant cache keys when a todo is created/updated/deleted.
4. **Never cache user-specific results** in a shared cache without namespacing by user ID.

For the workshop, caching is not needed — purely educational context.

---

## OpenAPI / Docs Standards

Document search parameters clearly:

```python
q: str | None = Query(
    default=None,
    min_length=1,
    max_length=100,
    description="Search todos by title keyword (case-insensitive).",
    examples=["groceries", "buy milk"],
)
```

---

## What NOT to Do

| Anti-pattern                        | Problem                                       |
|-------------------------------------|-----------------------------------------------|
| `POST /search` with body            | Search is a read — GET is correct             |
| Return 404 for empty results        | Confuses clients; 200 + empty list is right   |
| Load all rows then filter in Python | Defeats the database; O(n) memory usage       |
| Raw string interpolation in SQL     | SQL injection vulnerability                   |
| Separate duplicated search endpoint | Doubles maintenance burden                    |

---

*Created: 2026-02-22*
