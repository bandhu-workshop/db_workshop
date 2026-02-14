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

# 🔟 🧠 Permanent Thumb Rules (Memorize These)

1️⃣ API handles HTTP. CRUD handles database.  
2️⃣ CRUD never uses `Depends`.  
3️⃣ CRUD returns ORM models, not Pydantic schemas.  
4️⃣ Session lifecycle belongs to dependency, not CRUD.  
5️⃣ FastAPI serializes ORM models using `response_model`.  
6️⃣ Never mix response shapes if `response_model` is declared.  
7️⃣ Separation of concerns = production-ready mindset.

---
