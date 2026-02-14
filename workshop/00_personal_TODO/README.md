# 🧩 Handling 'Not Found' (CRUD vs API Layer)

• CRUD functions should NOT raise HTTP exceptions or handle HTTP status codes.  
• If a record is not found, CRUD returns None (or False).  
• The API (route) layer is responsible for raising HTTPException (e.g., 404) if needed.  
• This keeps the CRUD layer pure and reusable in non-HTTP contexts (CLI, background jobs, tests).

> 🏅 Golden Rule: CRUD handles data existence, API handles HTTP responses.

# 1️⃣ 🏗️ Application Architecture

We follow a clean layered architecture:

```
🔹 API Layer   → FastAPI (routes, Depends, response_model)
🔹 CRUD Layer  → Pure database logic
🔹 DB Layer    → Engine, SessionLocal, Models
```

## 1.1 🤔 Why Layering Matters?

• 🛠️ Keeps code maintainable  
• 🚫 Prevents tight coupling  
• 🧪 Makes testing easier  
• 📈 Scales to larger systems  
• 🔄 Allows replacing FastAPI without rewriting DB logic

> 🏅 Golden Rule: API talks HTTP. CRUD talks database.

---

# 2️⃣ 🚀 Database Initialization

## 2.1 ❓ Why initialize DB at startup?

Because:

• 🏗️ Tables should be created once  
• 🚫 Not per request  
• 🚫 Not manually  
• 🚫 Not randomly

## 2.2 ⚡ Typical Startup Tasks

• 🗄️ Create database tables  
• 🔗 Initialize connection pools  
• 🤖 Load ML models  
• 🟢 Connect to Redis  
• 🔥 Warm cache

We use FastAPI lifespan for startup logic.

---

# 3️⃣ 🧠 CRUD Layer Architecture

## 3.1 📋 Responsibilities of CRUD Layer

• Accepts SQLAlchemy `Session`  
• Uses ORM models  
• Performs add / commit / refresh / delete  
• Returns ORM model objects

## 3.2 🚫 What CRUD Must NOT Do

• Use `Depends()`  
• Import FastAPI  
• Raise HTTP exceptions  
• Convert to Pydantic schemas  
• Manage session lifecycle

---

# 4️⃣ 🔑 Session Management Rule

Session lifecycle is managed by FastAPI dependency:

```
get_db() → creates session  
request ends → session closes automatically
```

Therefore:

• CRUD uses session  
• CRUD never opens or closes session  
• CRUD never wraps session in `with`

> 🏅 Golden Rule: If FastAPI created the session, CRUD must not manage it.

---

# 5️⃣ 🔄 Write vs Read Rule

## 5.1 ✍️ For CREATE / UPDATE / DELETE:

• `session.add()`  
• `session.commit()`  
• `session.refresh()` (if needed)

## 5.2 👀 For READ:

• No commit

> 🏅 Golden Rule: Reads don’t commit. Writes always commit.

---

# 6️⃣ ✏️ Partial Update Rule

Use:

```
model_dump(exclude_unset=True)
```

Why?

• Updates only provided fields  
• Prevents overwriting existing values with `None`

> 🏅 Golden Rule: Never overwrite fields unintentionally.

---

# 7️⃣ 🧩 Handling 'Not Found' (CRUD vs API Layer)

• CRUD functions should NOT raise HTTP exceptions or handle HTTP status codes.  
• If a record is not found, CRUD returns None (or False).  
• The API (route) layer is responsible for raising HTTPException (e.g., 404) if needed.  
• This keeps the CRUD layer pure and reusable in non-HTTP contexts (CLI, background jobs, tests).

> 🏅 Golden Rule: CRUD handles data existence, API handles HTTP responses.

---

# 8️⃣ 🔁 Data Flow Mental Model

```
Client Request
        ↓
FastAPI Route (validation + dependency injection)
        ↓
CRUD (pure DB logic)
        ↓
Database
        ↓
FastAPI applies response_model (Pydantic validation + serialization)
        ↓
JSON Response to Client
```

• FastAPI automatically converts returned SQLAlchemy ORM models into the declared `response_model`.  
• This works because `orm_mode=True` (Pydantic v1) or `from_attributes=True` (Pydantic v2) is enabled.  
• CRUD returns ORM models.  
• FastAPI handles serialization into Pydantic schema.  
• Routes should return ORM objects directly — not manually call `.from_orm()`.

> 🏅 Golden Rule: CRUD returns models. FastAPI enforces the API contract.

---

# 9️⃣ 🌐 API Response Best Practices

## 9.1 📦 response_model Rule

If you declare:

```
response_model=TodoResponse
```

You must return the resource object directly — not wrap it inside a dict.

✔ Correct:

```
return todo_item
```

❌ Incorrect:

```
return {"message": "...", "todo": todo_item}
```

Why?

• REST APIs return resource representations  
• response_model defines a strict contract  
• FastAPI validates and serializes automatically

---

## 9.2 📡 Proper HTTP Status Codes

| Operation | Status Code | Response Body  |
| --------- | ----------- | -------------- |
| CREATE    | 201         | Created object |
| READ      | 200         | Object         |
| UPDATE    | 200         | Updated object |
| DELETE    | 204         | No content     |
| NOT FOUND | 404         | Error detail   |

• 204 is preferred for DELETE when no body is returned.  
• Never return empty objects when resource does not exist — raise 404 instead.

> 🏅 Golden Rule: API contracts must be consistent and predictable.

---

# 🔟 🔁 Idempotency: Safe Retries with Idempotency-Key

## What is Idempotency?

**Definition**: Same input → Same result (every time), no duplicates.

**Why it matters**: Network failures cause retries. Without idempotency:
- POST /pay twice → Charged twice 💀
- POST /todos twice → 2 identical todos ❌

---

## How We Implemented It

**Concept**: Use an `Idempotency-Key` header + cache table

```
Client sends: POST /todos with Header: Idempotency-Key: uuid-1
Server logic: 
  1. Check cache: "Have I seen uuid-1 before?"
  2. If YES:  Return cached todo (NO new creation!)
  3. If NO:   Create new todo + store uuid-1→todo_id mapping

Result: 3 identical requests → 1 todo ✅
```

**Files changed**:
- Added `TodoIdempotency` model (cache table)
- Added `create_todo_with_idempotency()` function
- Updated POST endpoint to accept `Idempotency-Key` header

## 🎯 Key Takeaways

> 🏅 **Golden Rule**: Same Idempotency-Key → Same Result (always!)

1. **Idempotency-Key Header**: Optional UUID from client
2. **Cache Table**: Stores key → todo ID mapping
3. **Check First**: Query cache before creating
4. **Create Once**: Only create if key not found
5. **Store Mapping**: Save key for future retries
6. **Return Same**: Always return 201 with same todo

---

## Your API Status

| Endpoint | Idempotent? |
|----------|-----------|
| GET `/todos/{id}` | ✅ YES (read-only) |
| PUT `/todos/{id}` | ✅ YES (replaces state) |
| DELETE `/todos/{id}` | ✅ YES (always 204) |
| POST `/todos` | ✅ YES (with idempotency-key) |

**100% idempotent!** 🚀

---

## 📚 Learn More

See detailed docs in workspace root:
- `IDEMPOTENCY_QUICK_REFERENCE.md` → Quick overview
- `IDEMPOTENCY_WORKFLOW_COMPLETE.md` → Deep dive
- `localdev/docs/idempotency/CURRENT_STATE_ANALYSIS.md` → Implementation analysis

---

# 1️⃣1️⃣ 🧠 How to Identify Idempotency (Your Framework)

Ask yourself for any endpoint:

```
1. Can I call this 3x with same input?  
2. Will system be in identical state?  
3. Will it create duplicates?  
4. Will it double-charge?  
5. Can I safely retry on failure?  
```

If all answers are YES ✅ → Idempotent
If any answer is NO ❌ → Not idempotent

👉 Add idempotency tests to CI/CD → Verify it works
👉 Document Idempotency-Key header → Client guidance

---

# 1️⃣2️⃣ 🧠 Alembic (SQLAlchemy's migration tool)

**Why**:
- Tracks all schema changes in version control
- Provides rollback capabilities
- Documents when/why changes were made
- Works with all database systems (SQLite, PostgreSQL, MySQL, etc.)
- Team-friendly: Everyone applies same migrations in same order

**Workflow**:
```
Code Change → Create Migration → Review Migration → Apply Migration → Commit Migration File
```

**Alembic Features**:
- Auto-generates migrations from model changes
- Manual migration control for complex changes
- Environment-aware application (dev, staging, prod)
- Upgrade/downgrade capability


# 1️⃣3️⃣ 🧠 Permanent Thumb Rules (Memorize These)

1️⃣ API handles HTTP. CRUD handles database.  
2️⃣ CRUD never uses `Depends`.  
3️⃣ CRUD returns ORM models, not Pydantic schemas.  
4️⃣ Session lifecycle belongs to dependency, not CRUD.  
5️⃣ FastAPI serializes ORM models using `response_model`.  
6️⃣ Never mix response shapes if `response_model` is declared.  
7️⃣ Separation of concerns = production-ready mindset.

---
