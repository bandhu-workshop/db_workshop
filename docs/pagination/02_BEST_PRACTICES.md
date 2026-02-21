# Best Practices and Industry Standards for Pagination

---

## 1. The Standard Response Envelope

The single most important best practice is: **never return a bare list for paginated endpoints**.

### Bad — bare list (what you have now)

```json
GET /todos

[
  { "id": 1, "title": "Buy milk", ... },
  { "id": 2, "title": "Read book", ... },
  ...
]
```

The client receives data but has **no idea**:
- How many items exist in total?
- Is there a next page?
- What page are they on?

This forces the client to keep guessing or make extra API calls.

---

### Good — paginated envelope (industry standard)

```json
GET /todos?page=1&limit=10

{
  "data": [
    { "id": 1, "title": "Buy milk", ... },
    { "id": 2, "title": "Read book", ... }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total_items": 47,
    "total_pages": 5,
    "has_next": true,
    "has_previous": false
  }
}
```

Every field in `pagination` serves a purpose:

| Field | Why it matters |
|---|---|
| `page` | Client can display "Page 1 of 5" |
| `limit` | Client knows the page size (their request may have been capped) |
| `total_items` | Client can build "47 results found" text |
| `total_pages` | Client can render a page-number nav widget |
| `has_next` | Client knows whether to show "Next →" button |
| `has_previous` | Client knows whether to show "← Prev" button |

---

## 2. How the Industry Names Things

There are two common naming conventions. Both are valid. Pick one and never mix them.

### Convention A — Page-based (most readable, recommended for most apps)

```
GET /todos?page=1&limit=10
```

- `page` — which page (1-based, not 0-based)
- `limit` — how many items per page

### Convention B — Offset-based (more explicit, maps directly to SQL)

```
GET /todos?offset=0&limit=10
```

- `offset` — how many items to skip
- `limit` — how many items to return

**Recommendation:** Use page-based. Clients find it more natural ("go to page 3" vs. "go to offset 20"). `offset` is an implementation detail that leaks your SQL.

---

## 3. What GitHub, Stripe, and Twitter Do

### GitHub API

```
GET /repos/{owner}/{repo}/issues?page=1&per_page=30
```

GitHub uses `page` and `per_page`. They also include `Link` headers for navigation:

```
Link: <https://api.github.com/issues?page=2>; rel="next",
      <https://api.github.com/issues?page=47>; rel="last"
```

### Stripe API

```
GET /v1/charges?limit=10&starting_after=ch_abc123
```

Stripe uses cursor-based pagination with `starting_after` (the ID of the last seen item) and `ending_before`. Their response:

```json
{
  "object": "list",
  "data": [...],
  "has_more": true,
  "url": "/v1/charges"
}
```

### Twitter/X API v2

```
GET /2/tweets?max_results=10&pagination_token=abc123xyz
```

Twitter uses cursor-based with opaque `pagination_token`. Their response includes `meta`:

```json
{
  "data": [...],
  "meta": {
    "result_count": 10,
    "next_token": "abc123xyz",
    "previous_token": "xyz321abc"
  }
}
```

### FastAPI's own documentation examples

FastAPI's docs suggest query parameters with defaults:

```python
@router.get("/items/")
async def read_items(skip: int = 0, limit: int = 100):
    return fake_items_db[skip : skip + limit]
```

They use flat query params (no wrapper schema). This is the minimal approach — fine for tutorials, but production should use the envelope pattern.

---

## 4. Rules for Query Parameters

### Set a Default Page Size

Never let the client control an unlimited response. Always have a default:

```python
# Good
def list_todos_endpoint(page: int = 1, limit: int = 10):
    ...
```

### Cap the Maximum Page Size

Even if a client sends `limit=99999`, cap it server-side:

```python
# Good — cap at 100
MAX_LIMIT = 100
actual_limit = min(limit, MAX_LIMIT)
```

Without this cap, one malicious (or accidental) request can bring down your server.

### Use 1-Based Page Numbers (not 0-based)

`page=1` is the first page. `page=0` is confusing and unconventional.

```
✅ ?page=1   (first page)
❌ ?page=0   (confusing — is this the first or invalid?)
```

### Validate Inputs

```python
# page must be >= 1, limit must be >= 1 and <= MAX_LIMIT
# If someone sends ?page=-5, return a 422 Unprocessable Entity
```

FastAPI + Pydantic handles this easily with `ge` (greater-or-equal) validators.

---

## 5. The COUNT(*) Question

To compute `total_items` and `total_pages`, you need to run a count query:

```sql
SELECT COUNT(*) FROM todos WHERE deleted_at IS NULL;
```

This is an extra database round-trip. Tradeoff:

| Approach | Pros | Cons |
|---|---|---|
| Always count | Client knows total pages | Extra DB query per request |
| Never count | Faster response | Client cannot show "Page X of Y" |
| Count only first page | First request is slower, rest are fast | Requires client to cache total |
| Optional `?include_count=true` | Client controls it | API surface complexity |

**Industry standard for CRUD apps:** Always count. The query is fast (COUNT on indexed column is cheap). Only optimize away the count if profiling shows it's a bottleneck.

---

## 6. Always Sort Your Results

Pagination **requires** a deterministic sort order. Without it, the database can return rows in any order, and the same row might appear on multiple pages or be skipped entirely.

```python
# Bad — results are non-deterministic:
query.offset(0).limit(10).all()

# Good — always sort:
query.order_by(Todo.created_at.desc(), Todo.id.desc()).offset(0).limit(10).all()
```

**Conventions:**
- For todo lists: `ORDER BY created_at DESC` (newest first is most natural)
- Add `id DESC` as a tiebreaker when `created_at` values could be identical
- Allow the client to change direction: `?sort=asc` or `?sort=desc`

---

## 7. HTTP Status Codes

| Situation | Status Code |
|---|---|
| Valid page with results | `200 OK` |
| Valid page but empty results (page 99 of a 5-page dataset) | `200 OK` with `"data": []` |
| Invalid page number (`?page=-1`) | `422 Unprocessable Entity` |
| Invalid limit (`?limit=abc`) | `422 Unprocessable Entity` |

**Important:** Do **not** return `404 Not Found` for an empty page. Empty is a valid state. Return `200` with an empty `data` array.

---

## 8. API Documentation

Document the defaults and constraints in your route's docstring and OpenAPI schema. With FastAPI + Pydantic this is automatic if you use `Query(ge=1, le=100, description="...")` annotations.

---

## 9. Checklist

Before shipping pagination to production:

- [ ] Query parameters have sensible defaults (`page=1`, `limit=10`)
- [ ] Maximum page size is server-enforced (never client-controlled)
- [ ] Results are always sorted by a deterministic column
- [ ] Response includes the pagination envelope (not a bare list)
- [ ] `total_items`, `total_pages`, `has_next`, `has_previous` are all computed
- [ ] Empty pages return `200 OK` with `data: []`
- [ ] Invalid inputs (negative page, non-integer limit) return `422`
- [ ] Both the data query AND the count query filter by the same `WHERE` clause

---

> Prev: [01_TYPES_OF_PAGINATION.md](./01_TYPES_OF_PAGINATION.md)  
> Next: [03_APPLIED_TO_YOUR_PROJECT.md](./03_APPLIED_TO_YOUR_PROJECT.md) — how all of this maps to your specific codebase.

---
*Created: 2026-02-21*
