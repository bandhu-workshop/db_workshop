# Types of Pagination — Strategies, Tradeoffs, and When to Use Each

There are three main strategies used in the industry. Each solves a different problem and comes with different tradeoffs.

---

## Strategy 1: Offset / Limit Pagination

### What It Is

The simplest and most common form. You tell the database to **skip N rows** and return the next M rows.

**API Surface:**

```
GET /todos?page=2&limit=10
GET /todos?offset=10&limit=10   ← same thing, different naming
```

**What happens under the hood (SQL):**

```sql
-- Page 1 (first 10 items)
SELECT * FROM todos WHERE deleted_at IS NULL
ORDER BY id ASC
LIMIT 10 OFFSET 0;

-- Page 2 (items 11-20)
SELECT * FROM todos WHERE deleted_at IS NULL
ORDER BY id ASC
LIMIT 10 OFFSET 10;

-- Page 3 (items 21-30)
SELECT * FROM todos WHERE deleted_at IS NULL
ORDER BY id ASC
LIMIT 10 OFFSET 20;
```

**The formula:**

```
offset = (page - 1) * limit
```

**SQLAlchemy version (Python):**

```python
query.offset(offset).limit(limit).all()
```

---

### Visual

```
Full dataset: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15 ...]

GET ?page=1&limit=5  → OFFSET 0  → [1, 2, 3, 4, 5]
GET ?page=2&limit=5  → OFFSET 5  → [6, 7, 8, 9, 10]
GET ?page=3&limit=5  → OFFSET 10 → [11, 12, 13, 14, 15]
```

---

### Advantages

- Simple to understand and implement
- Easy to jump to any page: "Go to page 47"
- Easy to count total pages: `total_pages = ceil(total_items / limit)`
- Works with all SQL databases out of the box
- Easy to test

---

### Weaknesses

#### 1. The "Phantom Row" Problem (Data Shifts)

Imagine you are on page 2 while someone adds a new todo at the top (newest first):

```
Before your page 2 request:            After a new item is inserted:
Page 1: [item10, item9, item8 ...]     Page 1: [NEW, item10, item9 ...]
Page 2: [item7, item6, item5 ...]      Page 2: [item8, item7, item6 ...]  ← item8 repeated!
```

You will see `item8` twice — once at the bottom of page 1 and once at the top of page 2. This is called **page drift**.

#### 2. Performance Degrades at Large Offsets

`OFFSET 100000 LIMIT 10` doesn't mean the DB only reads 10 rows. The database must:
1. Scan 100,010 rows
2. Discard the first 100,000
3. Return the last 10

The bigger the offset, the slower the query — even with indexes.

```
OFFSET 0      → nearly instant
OFFSET 1000   → fast
OFFSET 10000  → noticeable
OFFSET 100000 → slow
OFFSET 1000000→ very slow
```

---

### When to Use Offset/Limit

✅ Todo apps, blog posts, admin dashboards  
✅ When the dataset grows slowly (or data doesn't shift mid-browse)  
✅ When users need "jump to page X" navigation  
✅ When the dataset is < 1 million rows  
✅ **Your current project — this is the right choice for you**  

---

---

## Strategy 2: Cursor-Based Pagination

### What It Is

Instead of saying "skip N rows," you say "give me everything **after** this specific item." The "cursor" is usually the ID or timestamp of the last item you saw.

**API Surface:**

```
GET /todos?limit=10                          ← first page (no cursor)
GET /todos?limit=10&cursor=eyJpZCI6IDEwfQ== ← next page (base64-encoded cursor)
```

The server encodes the cursor (e.g., `{"id": 10}`) as a base64 string and returns it. The client sends it back on the next request.

**What happens under the hood (SQL):**

```sql
-- First page
SELECT * FROM todos WHERE deleted_at IS NULL
ORDER BY id ASC
LIMIT 10;

-- Next page (after id=10)
SELECT * FROM todos WHERE deleted_at IS NULL AND id > 10
ORDER BY id ASC
LIMIT 10;
```

---

### Visual

```
Full dataset: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 ...]

GET ?limit=5              → [1, 2, 3, 4, 5]    next_cursor = "id:5"
GET ?limit=5&cursor=id:5  → [6, 7, 8, 9, 10]   next_cursor = "id:10"
GET ?limit=5&cursor=id:10 → [11, 12, 13, 14, 15] next_cursor = "id:15"
```

---

### Advantages

- **No page drift**: Since we anchor on a specific ID, newly inserted items don't shift your position.
- **Consistent performance**: The `WHERE id > X` query uses the index efficiently regardless of how deep into the dataset you are.
- **Stable for real-time data**: Feeds, activity logs, chat messages all benefit.

---

### Weaknesses

- Cannot jump to a specific page ("Show me page 47" is impossible)
- Cannot show "Page 2 of 47" — you don't know the total easily
- More complex to implement
- Cursors must be opaque (you usually base64-encode them)
- Harder to debug

---

### When to Use Cursor-Based

✅ Social media feeds (Twitter/X, Instagram)  
✅ Chat messages, activity logs  
✅ Real-time data that changes frequently  
✅ Very large datasets (> 1 million rows)  
✅ Infinite scroll UI patterns  
❌ Admin panels where users need "go to page X"  
❌ Simple CRUD apps like a personal todo list  

---

---

## Strategy 3: Keyset Pagination (a.k.a. Seek Method)

### What It Is

A more sophisticated version of cursor-based pagination. Instead of encoding a cursor, you pass the actual last values directly as query parameters.

**API Surface:**

```
GET /todos?limit=10
GET /todos?limit=10&last_id=10&last_created_at=2026-02-21T10:00:00Z
```

**SQL:**

```sql
-- First page
SELECT * FROM todos WHERE deleted_at IS NULL
ORDER BY created_at DESC, id DESC
LIMIT 10;

-- Next page (keyset: after this specific item)
SELECT * FROM todos
WHERE deleted_at IS NULL
  AND (created_at, id) < ('2026-02-21T10:00:00Z', 10)
ORDER BY created_at DESC, id DESC
LIMIT 10;
```

---

### When to Use Keyset

✅ High-performance systems (Stripe uses this for their API)  
✅ When you need strict, stable ordering on multiple columns  
✅ Very high-traffic APIs  
❌ Overkill for most applications  

---

---

## Strategy Comparison Table

| Feature | Offset/Limit | Cursor-Based | Keyset |
|---|---|---|---|
| **Complexity** | Low | Medium | High |
| **Jump to page** | ✅ Yes | ❌ No | ❌ No |
| **Show total count** | ✅ Easy | ⚠️ Expensive | ⚠️ Expensive |
| **Stable under inserts** | ❌ No | ✅ Yes | ✅ Yes |
| **Performance at depth** | ❌ Degrades | ✅ Consistent | ✅ Best |
| **Infinite scroll** | ⚠️ OK | ✅ Perfect | ✅ Perfect |
| **Best for** | Admin UIs, CRUDs | Feeds, chat | High-perf APIs |
| **Used by** | Most apps | Twitter, Slack | Stripe |
| **Your project** | ✅ **Use this** | ❌ Overkill | ❌ Overkill |

---

## Summary: What Should You Use?

For your personal todo API, **offset/limit pagination is the correct choice**:

- Your dataset is small and grows slowly
- Users might want "page 2 of 5" style navigation
- You want the simplest, most teachable solution
- You don't have a real-time feed with concurrent writes

The weaknesses of offset/limit (page drift, deep offset performance) are not relevant problems at this scale.

---

> Prev: [00_WHAT_IS_PAGINATION.md](./00_WHAT_IS_PAGINATION.md)  
> Next: [02_BEST_PRACTICES.md](./02_BEST_PRACTICES.md) — the industry-standard response format and naming conventions.

---
*Created: 2026-02-21*
