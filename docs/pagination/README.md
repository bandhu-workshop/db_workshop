# Pagination — Learning Guide

A complete, ground-up guide to pagination in the context of this FastAPI + SQLAlchemy todo project.

---

## Reading Order

| # | File | What You Will Learn |
|---|---|---|
| 0 | [00_WHAT_IS_PAGINATION.md](./00_WHAT_IS_PAGINATION.md) | The problem, the analogy, the four reasons pagination exists |
| 1 | [01_TYPES_OF_PAGINATION.md](./01_TYPES_OF_PAGINATION.md) | Offset/Limit vs. Cursor vs. Keyset — when to use each |
| 2 | [02_BEST_PRACTICES.md](./02_BEST_PRACTICES.md) | Industry standards: response envelope, naming, GitHub/Stripe/Twitter patterns |
| 3 | [03_APPLIED_TO_YOUR_PROJECT.md](./03_APPLIED_TO_YOUR_PROJECT.md) | How pagination maps to your exact code, layer by layer |

---

## Key Concepts at a Glance

**The core idea:**
> Return a small, predictable slice of data instead of everything.

**The formula (offset/limit):**
```
offset = (page - 1) * limit
```

**The standard response shape:**
```json
{
  "data": [...],
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

**The layers that change:**
- `schemas.py` — new response envelope schema
- `todo_crud.py` — returns `(todos, total)` instead of all todos
- `todo_api.py` — new `page` and `limit` query params

**The layer that does NOT change:**
- `models.py` — the database model is untouched

---

## Decision Summary

| Question | Answer |
|---|---|
| Which pagination strategy? | Offset/Limit |
| Query params? | `page` (default: 1) and `limit` (default: 10) |
| Max limit? | 100 |
| Sort order? | `created_at DESC, id DESC` (newest first) |
| Empty page status code? | `200 OK` with `data: []` |
| Return bare list or envelope? | Envelope with `pagination` metadata |

---

*Created: 2026-02-21*
