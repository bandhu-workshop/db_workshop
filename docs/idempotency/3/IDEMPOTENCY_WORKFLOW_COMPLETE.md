# 🔁 Idempotency Workflow Explained

## 🎯 What is Idempotency?

**Simple Definition:**
> Calling an operation multiple times with identical inputs produces the same result as calling it once.

**Mathematically:**
$$f(f(x)) = f(x) = f(f(f(x))) = \ldots$$

**In Plain English:**
```
First call  → Result X
Retry call  → Result X (SAME!)
Retry again → Result X (STILL SAME!)
```

---

## 🌍 Why Does Idempotency Matter?

In real-world distributed systems, **failures are inevitable**:

```
Network timeouts
├─ Client doesn't know if request succeeded
└─ Automatic retry kicks in

Load balancer failover
├─ Request goes to Server A
├─ Server A crashes after processing
├─ Request retried on Server B
└─ Could create duplicates!

Mobile app retries
├─ App detects connection loss
├─ Automatically retries request
└─ Needs to be safe

User double-clicking button
├─ User clicks fast
├─ Both clicks sent to server
└─ Should result in 1 action, not 2
```

**Without idempotency:**
- POST /pay twice → Customer charged twice 💀
- POST /orders twice → 2 identical orders ❌
- DELETE twice → 404 error on second call ⚠️

**With idempotency:**
- Same input → Same result guaranteed ✅
- Safe to retry any time ✅
- No duplicates ✅

---

## 🔄 Our Implementation: The Workflow

We implemented idempotency for POST /todos using an **idempotency-key** pattern (used by Stripe, PayPal, AWS, etc.).

### Step 1: Client Includes Idempotency Key

```bash
POST /todos
Header: Idempotency-Key: abc-123-xyz-random-uuid
Body: {
  "title": "Buy milk",
  "description": "From grocery store"
}
```

**Why generate a key?**
- Each POST request gets a unique ID (UUID)
- Client sends same key if retrying
- Server uses key to deduplicate

---

### Step 2: Server Checks Cache

When POST request arrives, server does:

```python
# Step 1: Check if we've seen this idempotency key before
existing_todo = session.query(TodoIdempotency).filter(
    TodoIdempotency.idempotency_key == "abc-123-xyz-random-uuid"
).first()

if existing_todo:
    # KEY EXISTS! Return cached result (IDEMPOTENT)
    return get_cached_todo(existing_todo.todo_id)
else:
    # KEY NOT FOUND! Create new todo
    # ... continue to Step 3
```

**Two Possible Paths:**

```
┌─────────────────────────────────────┐
│ POST Request with Idempotency-Key   │
└────────────┬────────────────────────┘
             │
             ▼
    ┌───────────────────┐
    │ Check Database    │
    │ for this key?     │
    └──┬──────────────┬─┘
       │              │
   YES │              │ NO
       │              │
       ▼              ▼
    ┌────────┐    ┌──────────────┐
    │ CACHE  │    │ CREATE NEW   │
    │ HIT    │    │ TODO RECORD  │
    │        │    │              │
    │Return  │    │ Store key→id │
    │cached  │    │ mapping      │
    │todo    │    │              │
    └────┬───┘    └──────┬───────┘
         │               │
         └───────┬───────┘
                 ▼
        ┌──────────────────┐
        │ Return same todo │
        │ (IDEMPOTENT!) ✅ │
        └──────────────────┘
```

---

### Step 3: Create New Todo (If Not Cached)

```python
# Create new todo record
todo = Todo(
    title="Buy milk",
    description="From grocery store",
    is_completed=False
)
session.add(todo)
session.commit()  # Now has ID, e.g., todo.id = 42
```

---

### Step 4: Store Idempotency Key

```python
# Store mapping: key → todo_id
# This is the CRITICAL piece that enables idempotency!
idempotency_record = TodoIdempotency(
    idempotency_key="abc-123-xyz-random-uuid",
    todo_id=42  # The ID of newly created todo
)
session.add(idempotency_record)
session.commit()

# Now database has:
# ┌─────────────────────────────────────────────┐
# │ todos table                                 │
# ├─────────────────────────────────────────────┤
# │ id: 42                                      │
# │ title: "Buy milk"                           │
# │ created_at: 2026-02-15 10:30:00            │
# └─────────────────────────────────────────────┘
#
# ┌──────────────────────────────────────────────┐
# │ todo_idempotency_keys table                  │
# ├──────────────────────────────────────────────┤
# │ id: 1                                        │
# │ idempotency_key: "abc-123-xyz-random-uuid"  │
# │ todo_id: 42  ← points to todo above         │
# │ created_at: 2026-02-15 10:30:00            │
# └──────────────────────────────────────────────┘
```

---

### Step 5: Return Response

```python
# Return the created todo (response always 201)
return TodoResponse(
    id=42,
    title="Buy milk",
    description="From grocery store",
    is_completed=False,
    created_at="2026-02-15T10:30:00Z"
)
```

---

## 📊 Database Schema

### todos table
```
┌────┬──────────────┬────────────────────────┬──────────────┐
│ id │ title        │ description            │ is_completed │
├────┼──────────────┼────────────────────────┼──────────────┤
│ 1  │ Buy milk     │ From grocery store     │ false        │
│ 2  │ Call doctor  │ Annual checkup         │ true         │
│ 42 │ Buy milk     │ From grocery store     │ false        │ ← Same data as id=1!
└────┴──────────────┴────────────────────────┴──────────────┘
```

### todo_idempotency_keys table
```
┌────┬───────────────────────────┬─────────┐
│ id │ idempotency_key           │ todo_id │
├────┼───────────────────────────┼─────────┤
│ 1  │ abc-123-xyz-random-uuid   │ 42      │
│ 2  │ def-456-uvw-another-uuid  │ 2       │
└────┴───────────────────────────┴─────────┘
```

**Key Relationship:**
```
idempotency_key → todo_id
↓
"abc-123-xyz-random-uuid" → 42
```

When same key comes again:
1. Query finds the record: `idempotency_key = "abc-123-xyz-random-uuid"`
2. Get the `todo_id = 42`
3. Return todo with id=42 (no new creation)

---

## 🔍 Complete Workflow Example

### Scenario: First Request

```
CLIENT                          SERVER                    DATABASE
   │                              │                            │
   │─ POST /todos   ─────────────►│                            │
   │  Header:                     │                            │
   │  Idempotency-Key: UUID-1     │                            │
   │  Body: {title: "Buy milk"}   │                            │
   │                              │                            │
   │                              ├─ Check idempotency_keys    │
   │                              │  for UUID-1                │
   │                              ├─────────────────────────►  │
   │                              │  NOT FOUND                 │
   │                              │◄─────────────────────────┤
   │                              │                            │
   │                              ├─ CREATE new todo         │
   │                              ├─────────────────────────►│
   │                              │  INSERT into todos...    │
   │                              │  todo_id = 42            │
   │                              │  COMMIT                  │
   │                              │◄─────────────────────────┤
   │                              │                            │
   │                              ├─ STORE idempotency key  │
   │                              ├─────────────────────────►│
   │                              │  INSERT into             │
   │                              │  idempotency_keys...    │
   │                              │  key=UUID-1, todo_id=42 │
   │                              │  COMMIT                  │
   │                              │◄─────────────────────────┤
   │                              │                             │
   │◄─ 201 Created   ─────────────┤                            │
   │  {id: 42, title: "Buy milk"}│                            │
   │                              │                            │
```

### Scenario: Retry (Same Request)

```
CLIENT                          SERVER                    DATABASE
   │                              │                            │
   │─ POST /todos ─────────────►│                            │
   │  (Network failed before—)   │                            │
   │  Idempotency-Key: UUID-1   │                            │
   │  Body: {title: "Buy milk"} │                            │
   │                              │                            │
   │                              ├─ Check idempotency_keys  │
   │                              │  for UUID-1                │
   │                              ├─────────────────────────►│
   │                              │  FOUND! todo_id = 42     │
   │                              │◄─────────────────────────┤
   │                              │                            │
   │                              ├─ FETCH todo with id=42  │
   │                              ├─────────────────────────►│
   │                              │  SELECT * FROM todos     │
   │                              │  WHERE id = 42           │
   │                              │◄─────────────────────────┤
   │                              │                            │
   │◄─ 201 Created ─────────────┤                            │
   │  {id: 42, title: "Buy milk"}│ ← SAME AS FIRST CALL!   │
   │                              │                            │
   │  ✅ IDEMPOTENT!            │                            │
   │  Only 1 record created      │                            │
   │  in database despite        │                            │
   │  2 requests                 │                            │
```

---

## 🧪 Test: Proving Idempotency

```python
# Test 1: First POST
response_1 = client.post(
    "/todos",
    json={"title": "Buy milk"},
    headers={"Idempotency-Key": "uuid-1"}
)
assert response_1.status_code == 201
todo_id_1 = response_1.json()["id"]
# todo_id_1 = 42

# Test 2: Retry with SAME key
response_2 = client.post(
    "/todos",
    json={"title": "Buy milk"},
    headers={"Idempotency-Key": "uuid-1"}  # SAME KEY
)
assert response_2.status_code == 201  # Still 201!
todo_id_2 = response_2.json()["id"]
# todo_id_2 = 42 (SAME ID!)

# Assertion: Both responses identical
assert response_1.json() == response_2.json()  ✅

# Assertion: Only 1 todo created in database
todos = session.query(Todo).filter(Todo.title == "Buy milk").all()
assert len(todos) == 1  ✅ (not 2!)
```

---

## 🔑 Key Concepts

### 1. **Idempotency-Key Header**
- Optional UUID provided by client
- Unique identifier for this logical request
- If not provided, works normally but can't deduplicate

```bash
# Client generates UUID v4
uuid = uuid4()  # e.g., "550e8400-e29b-41d4-a716-446655440000"

# Send with request
POST /todos
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
```

---

### 2. **Cache Table**
- Maps idempotency keys to resource IDs
- Single record per unique key
- UNIQUE constraint ensures 1-to-1 mapping

```sql
CREATE TABLE todo_idempotency_keys (
    id INT PRIMARY KEY AUTO_INCREMENT,
    idempotency_key VARCHAR(50) UNIQUE NOT NULL,
    todo_id INT NOT NULL,
    FOREIGN KEY (todo_id) REFERENCES todos(id)
);
```

---

### 3. **The Check-Create-Store Flow**
```
1. CHECK:  Does key exist in cache? 
   → YES: Return cached todo (idempotent!)
   → NO: Continue

2. CREATE: Insert new todo into database
   → Get the ID of newly created todo

3. STORE:  Insert (key → ID) mapping into cache
   → Now future calls will find the key
```

---

## ✅ vs ❌ Idempotency Comparison

### ✅ IDEMPOTENT (Our Implementation)

```
Call 1: POST /todos with Idempotency-Key: uuid-1
        ├─ Key not found → Create todo 42
        └─ Store key → todo 42 mapping
        Response: 201, id: 42

Call 2: POST /todos with Idempotency-Key: uuid-1 (retry)
        ├─ Key found → Return todo 42
        └─ No new creation
        Response: 201, id: 42 ✅ SAME!

Call 3: POST /todos with Idempotency-Key: uuid-1 (retry again)
        ├─ Key found → Return todo 42
        └─ No new creation
        Response: 201, id: 42 ✅ STILL SAME!

Database state: 1 todo with id=42 (IDEMPOTENT!)
```

---

### ❌ NOT IDEMPOTENT (Before Implementation)

```
Call 1: POST /todos {title: "Buy milk"}
        → Create todo 1
        Response: 201, id: 1

Call 2: POST /todos {title: "Buy milk"} (retry)
        → Create todo 2 (DUPLICATE!)
        Response: 201, id: 2 ❌ DIFFERENT!

Call 3: POST /todos {title: "Buy milk"} (retry again)
        → Create todo 3 (ANOTHER DUPLICATE!)
        Response: 201, id: 3 ❌ DIFFERENT AGAIN!

Database state: 3 identical todos (NOT IDEMPOTENT!)
```

---

## 🎯 When to Use Idempotency-Key

| Scenario | Use Idempotency-Key? |
|----------|----------------------|
| Payments (POST /pay) | 🔴 **CRITICAL** |
| Creating orders (POST /orders) | 🔴 **CRITICAL** |
| Transferring money | 🔴 **CRITICAL** |
| Creating user accounts | 🟡 **Recommended** |
| Creating todos | 🟡 **Recommended** |
| Updating data (PUT) | 🟢 No (already idempotent) |
| Deleting data (DELETE) | 🟢 No (already idempotent) |
| Reading data (GET) | 🟢 No (already idempotent) |

---

## 🚀 Real-World Example: Stripe Payment API

Stripe (payment processor) uses this exact pattern:

```python
# Client code
import stripe

# Generate unique request ID
request_id = str(uuid4())

# Send payment with idempotency key
try:
    charge = stripe.Charge.create(
        amount=2000,          # $20.00
        currency="usd",
        source="tok_visa",
        idempotency_key=request_id  # ← THE KEY!
    )
except stripe.error.CardError:
    # Network failed, retry with SAME key
    charge = stripe.Charge.create(
        amount=2000,
        currency="usd",
        source="tok_visa",
        idempotency_key=request_id  # ← SAME KEY!
    )
    # Stripe returns cached result, no second charge!
```

**Result**: Customer charged $20 once, never twice ✅

---

## 📚 Summary

| Aspect | Detail |
|--------|--------|
| **What** | Ensure same input → same result, every time |
| **Why** | Network failures cause retries; must be safe |
| **How** | Use idempotency-key header + cache table |
| **Where** | Critical for POST, not needed for GET/PUT/DELETE |
| **When** | Implement before production traffic |
| **Cost** | Tiny (one extra lookup + cache storage) |
| **Benefit** | Production-grade reliability |

