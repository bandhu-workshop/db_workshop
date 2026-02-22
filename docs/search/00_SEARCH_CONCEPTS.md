# 00 — Search in Databases: Core Concepts

## What Is "Search"?

Search means filtering rows where a column **contains** a given keyword —
rather than matching it exactly.

| Approach         | SQL Operator      | Case-insensitive? | Wildcard? | Speed    |
|------------------|-------------------|--------------------|-----------|----------|
| Exact match      | `= 'value'`       | No                 | No        | Fastest  |
| Pattern match    | `LIKE '%val%'`    | Database-dependent | Yes (`%`) | Slow     |
| Case-insensitive | `ILIKE '%val%'`   | Yes (PostgreSQL)   | Yes       | Slow     |
| Full-text search | `tsvector` / FTS  | Yes                | Stemming  | Fast*    |
| Trigram index    | `pg_trgm`         | Yes                | Yes       | Fast*    |

> *Fast when properly indexed.

---

## 1. LIKE / ILIKE — The Simple Approach

```sql
-- Find todos whose title contains "buy"
SELECT * FROM todos WHERE title LIKE '%buy%';

-- Case-insensitive version (PostgreSQL)
SELECT * FROM todos WHERE title ILIKE '%buy%';
```

### How `%` Works (Wildcard)

| Pattern      | Matches                         |
|--------------|---------------------------------|
| `'buy%'`     | starts with "buy"               |
| `'%buy'`     | ends with "buy"                 |
| `'%buy%'`    | contains "buy" anywhere         |
| `'b_y'`      | b + any one char + y (`_` = 1)  |

### The Performance Problem

`LIKE '%value%'` with a **leading wildcard** (`%value`) **cannot use a B-tree
index** on the column. The database performs a full table scan — every row is
read and compared. Acceptable for small tables (< ~50 k rows); painful beyond.

---

## 2. Full-Text Search (FTS)

Full-text search goes beyond substring matching. The database tokenises text
into **lexemes** (word roots), stores them in a `tsvector`, and matches them
using a `tsquery`.

```sql
-- PostgreSQL FTS example
SELECT * FROM todos
WHERE to_tsvector('english', title) @@ to_tsquery('english', 'buy');
```

### What FTS Does That LIKE Cannot

- **Stemming**: "buying", "bought", "buys" → all match "buy"
- **Ranking**: results ordered by relevance score (`ts_rank`)
- **Stop words**: ignores "the", "a", "is" automatically
- **GIN index**: very fast even on large datasets

### When to Use FTS

- Searching **natural language** content (articles, notes, descriptions)
- Tables with **millions of rows**
- You need **relevance ranking**

---

## 3. Trigram Search (`pg_trgm`)

A trigram is every 3-character sequence in a string.  
`"hello"` → `" he"`, `"hel"`, `"ell"`, `"llo"`, `"lo "`.

```sql
-- Install extension (once)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create index
CREATE INDEX idx_todos_title_trgm ON todos USING GIN (title gin_trgm_ops);

-- Query (uses the index!)
SELECT * FROM todos WHERE title ILIKE '%buy%';
```

### Why Trigrams Are Useful

- Supports `LIKE '%val%'` with a leading wildcard **and still uses the index**
- Good for **fuzzy / typo-tolerant** matching
- Works with any substring, not just whole words

---

## 4. SQLite Specifics (used in this workshop)

SQLite's `LIKE` is **case-insensitive for ASCII letters by default**.  
There is no native `ILIKE` keyword — `LIKE` already behaves case-insensitively
for the ASCII range.

SQLite has a basic FTS extension called **FTS5** (available as `fts5` virtual
table), but it is only useful for full sentence search and requires a separate
virtual table.

For a small to medium todo app running on SQLite, **`LIKE '%keyword%'`** is
the right choice.

---

## 5. Decision Tree: Which to Use?

```
Dataset < 100k rows AND SQLite?
  └─ YES → LIKE '%keyword%'  ✅  (simple, adequate)
  └─ NO  → PostgreSQL?
               └─ YES, whole-word / natural language?
                         └─ YES → Full-Text Search (tsvector + GIN index)
                         └─ NO  → Substring / typo-tolerant?
                                       └─ YES → pg_trgm + GIN index
                                       └─ NO  → ILIKE (add pg_trgm index later)
```

---

## 6. Key Terms Glossary

| Term        | Meaning                                                          |
|-------------|------------------------------------------------------------------|
| `LIKE`      | SQL operator for pattern matching with `%` and `_` wildcards     |
| `ILIKE`     | Case-insensitive LIKE (PostgreSQL only)                          |
| `tsvector`  | PostgreSQL type that stores tokenised, stemmed words             |
| `tsquery`   | Query type that matches against a `tsvector`                     |
| `GIN index` | Generalised Inverted Index — fast for array/text containment     |
| Trigram     | All overlapping 3-char slices of a string, used for fuzzy search |
| Lexeme      | The root form of a word after stemming                           |
| Stop words  | Common words ignored by FTS (the, a, is, …)                     |

---

*Created: 2026-02-22*
