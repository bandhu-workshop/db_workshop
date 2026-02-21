# What Is Pagination and Why Do We Need It?

## 1. The Problem Without Pagination

Your current `list_todos` endpoint looks like this:

```python
@router.get("/", response_model=list[TodoResponse], status_code=200)
def list_todos_endpoint(session: Session = Depends(get_db)):
    return list_todos(session)
```

And the CRUD function:

```python
def list_todos(session: Session, include_deleted: bool = False) -> list[Todo]:
    query = session.query(Todo)
    if not include_deleted:
        query = query.filter(Todo.deleted_at.is_(None))
    return query.all()   # ← THE PROBLEM IS HERE
```

The `.all()` at the end tells the database:

> "Give me **every single row** in this table."

Right now you have maybe 5–10 todos. That is fine. But ask yourself: what happens in production?

---

## 2. The Scenario: What Goes Wrong

| Todos in DB | Time to query | Memory used | Network payload | User experience |
|-------------|--------------|-------------|-----------------|-----------------|
| 10          | ~1 ms        | negligible  | ~2 KB           | Instant         |
| 1,000       | ~10 ms       | ~500 KB     | ~200 KB         | Still fast      |
| 100,000     | ~800 ms      | ~50 MB      | ~20 MB          | Laggy           |
| 1,000,000   | >10 s        | ~500 MB     | ~200 MB         | Server crashes  |

The database has to:
1. **Scan** the entire `todos` table
2. **Load** every row into memory on the server
3. **Serialize** everything into JSON
4. **Send** the entire payload over the network
5. **Deserialize** everything on the client

This creates **three bottlenecks simultaneously**: database, server, and network.

---

## 3. The Real-World Analogy

Think of a library. You walk in and ask:

> "Give me every book you have."

Instead of handing you all 80,000 books at once, the librarian says:

> "Here are books 1–20. Which shelf do you want next?"

That is pagination. You ask for **a slice of data**, not all of it.

---

## 4. What Pagination Actually Is

Pagination is the practice of **dividing a large dataset into smaller, discrete chunks (pages)** and returning one page at a time.

A paginated API call looks like:

```
GET /todos?page=2&limit=10
```

The server returns:
- The 10 todos for page 2 (items 11–20)
- Metadata about the total dataset

The client can then ask for page 3, page 4, etc.

---

## 5. The Four Problems Pagination Solves

### Problem 1 — Database Memory Pressure

Without pagination, `SELECT * FROM todos` loads **all rows into RAM** on the database server. With thousands of concurrent users doing this, databases run out of memory and start failing.

With pagination, the query becomes:

```sql
SELECT * FROM todos WHERE deleted_at IS NULL LIMIT 10 OFFSET 0;
```

The database loads only the 10 rows you asked for and discards the rest.

### Problem 2 — Server Memory Pressure

Without pagination, SQLAlchemy builds a Python list of **every ORM object** in memory. Each `Todo` object might be ~1 KB. 100,000 todos = ~100 MB per request, per worker.

FastAPI typically runs 4–8 workers. That is potentially 800 MB for one endpoint's data alone.

### Problem 3 — Network Bandwidth

JSON is verbose. A 100,000-row response can easily be 50–200 MB. Mobile users on limited data plans will abandon the app. Slow network connections will time out.

Sending 10 items at ~2 KB is orders of magnitude cheaper.

### Problem 4 — User Experience

Nobody benefits from receiving 100,000 todo items at once — not a human looking at a UI, and not a client app parsing JSON. Pagination forces a natural "browse" flow that matches how humans actually consume information.

---

## 6. Pagination vs. The Alternatives

| Approach | What it does | Problem |
|---|---|---|
| No pagination (`query.all()`) | Returns everything | Explodes at scale |
| Client-side filtering | Returns everything, filters in JS | Still explodes at the API level |
| Streaming | Sends data as a stream | Complex, rarely needed for todo lists |
| **Pagination** | Server decides the slice | **Correct solution** |

---

## 7. Quick Visual

```
Full dataset (1,000 todos):
┌─────────────────────────────────────────────────────────────┐
│  1  2  3  4  5  6  7  8  9  10 | 11 12 13 ... 20 | 21 ...  │
│  ← ─ ─ ─ Page 1 ─ ─ ─ ─ ─ ─ → | ← ─ Page 2 ─ ─ → |        │
└─────────────────────────────────────────────────────────────┘

GET /todos?page=1&limit=10  →  returns items 1–10
GET /todos?page=2&limit=10  →  returns items 11–20
GET /todos?page=3&limit=10  →  returns items 21–30
```

---

## 8. What We Return Along With the Data

A raw list of items is not enough. The client needs to know:

- **How many items total exist?** (so it can render "Page 2 of 47")
- **Is there a next page?** (to know whether to show a "Load More" button)
- **What page am I on right now?**

This extra information is called **metadata** or a **pagination envelope**. See `02_BEST_PRACTICES.md` for the exact structure industry uses.

---

## 9. Summary

| Without Pagination | With Pagination |
|---|---|
| `SELECT * FROM todos` — all rows | `SELECT * FROM todos LIMIT 10 OFFSET 0` — 10 rows |
| Server loads everything into RAM | Server loads 10 items |
| 200 MB JSON payload | 2 KB JSON payload |
| Crashes at scale | Handles millions of rows |
| Bad UX (waiting for huge response) | Fast, predictable UX |

---

> Next: [01_TYPES_OF_PAGINATION.md](./01_TYPES_OF_PAGINATION.md) — the three main strategies and when to pick each one.

---
*Created: 2026-02-21*
