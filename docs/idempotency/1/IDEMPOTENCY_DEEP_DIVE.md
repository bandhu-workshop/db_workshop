# 🧠 Deep Dive: Idempotency Concepts & Patterns

---

## 📐 Mathematical Definition

An operation **f(x)** is idempotent if:

$$f(f(x)) = f(x) = f(f(f(x))) = \ldots$$

In plain language:
> Applying the operation multiple times = applying it once

### Examples

#### Idempotent ✅
```
abs(-5) = 5
abs(abs(-5)) = abs(5) = 5  ✅ Same!

delete_file("/tmp/test.txt")
delete_file("/tmp/test.txt")  ✅ Same state (gone)

set_is_completed_to_true(todo_5)
set_is_completed_to_true(todo_5)  ✅ Same state (completed)
```

#### NOT Idempotent ❌
```
increment_counter()  → 1
increment_counter()  → 2  ❌ Different!

create_invoice()  → INV-001
create_invoice()  → INV-002  ❌ Different!

POST /pay with $100
POST /pay with $100  → charged twice  ❌ Different!
```

---

## 🌐 Distributed Systems Reality

### Why Idempotency Matters

In a distributed system, any request can fail:

```
USER → [Network] → LOAD BALANCER → [Network] → SERVER → [Database]
                         ↓
                    Connection timeout?
                    Server crashed?
                    Network hiccup?
```

**Client automatic retry logic:**
```python
# Pseudo-code: what most HTTP clients do
for attempt in range(max_retries=3):
    try:
        response = send_request()
        return response
    except ConnectionError:
        wait(exponential_backoff)
```

### Scenario: Payment Without Idempotency 💀

```
Client sends: POST /charge with $100

Attempt 1:
  - Server receives request
  - Charges $100 ✅
  - Response sent... but network drops

Attempt 2 (automatic retry):
  - Client doesn't know if charge went through
  - Retries the same request
  - Server charges ANOTHER $100 ❌❌

Result: Customer charged $200 instead of $100!
```

### Solution: Idempotency Key

```
Client sends: POST /charge
  Header: Idempotency-Key: abc-123-xyz
  Body: $100

Attempt 1:
  - Server receives
  - Stores: "abc-123-xyz → charged $100"
  - Charges $100
  - Response sent... network drops

Attempt 2 (automatic retry):
  - Server checks: "Does abc-123-xyz exist?"
  - YES! Return same response ✅
  - No second charge

Result: Customer charged $100 (correct!)
```

---

## 🔄 HTTP Methods and Idempotency

### GET - Always Idempotent

```python
GET /todos/5
GET /todos/5 (retry)
GET /todos/5 (retry)

All return same data ✅
No side effects ✅
```

**Why**: GET has no side effects. It's read-only.

---

### POST - Never Idempotent (by design)

```python
POST /todos
POST /todos (retry)

Creates 2 todos ❌
Side effects every time
```

**Why**: POST is for creating new resources. By definition, it creates something new each time.

**How to make idempotent**: Add idempotency key tracking.

---

### PUT - Always Idempotent

```python
PUT /todos/5 { "title": "Updated", "done": true }
PUT /todos/5 { "title": "Updated", "done": true }  (retry)
PUT /todos/5 { "title": "Updated", "done": true }  (retry)

Final state = "Updated, done" (same!)  ✅
```

**Why**: PUT replaces entire resource. Same input = same state.

**Caveat**: Only if you send complete data, not partial.

---

### PATCH - Depends on Implementation

```python
❌ NOT Idempotent:
PATCH /todos/5 { "increment_views": 1 }
PATCH /todos/5 { "increment_views": 1 }
→ Views: 0 → 1 → 2  (different!)

✅ Idempotent:
PATCH /todos/5 { "set_title": "New Title" }
PATCH /todos/5 { "set_title": "New Title" }  (retry)
→ Title = "New Title" (same!)
```

**Rule**: PATCH is idempotent only if operations are "set" (replace), not "increment" or "append".

---

### DELETE - Should Be Idempotent

**The Tricky One**

```
❌ Current: Your API
DELETE /todos/5 → 204
DELETE /todos/5 (retry) → 404  (violates idempotency!)

✅ Correct:
DELETE /todos/5 → 204
DELETE /todos/5 (retry) → 204  (idempotent!)
```

**Philosophy**: The goal of DELETE is "ensure this resource doesn't exist"

Once it doesn't exist, that goal is achieved. Retrying doesn't change that.

```
Resource state after 1 delete: GONE
Resource state after 2 deletes: GONE (same!)
```

---

## 🏗️ Idempotency Key Pattern (Enterprise Level)

### How Stripe Does It

```python
# Client code (Stripe library)
import stripe

payment = stripe.Charge.create(
    amount=2000,
    currency="usd",
    source="tok_visa",
    idempotency_key="abc-123-xyz",  # Client generates UUID
)

# Server (Stripe's implementation)
def create_charge(data, idempotency_key):
    # Step 1: Check if we've seen this key before
    cached = redis.get(f"idempotency:{idempotency_key}")
    if cached:
        return cached  # Return previous response
    
    # Step 2: Create charge
    charge = db.charges.insert(data)
    
    # Step 3: Cache response
    redis.set(
        f"idempotency:{idempotency_key}",
        charge.response,
        expire=24*3600,  # Expire after 24 hours
    )
    
    return charge.response
```

---

## 🎯 Idempotency vs Idempotent Key

| Term | Meaning | Example |
|------|---------|---------|
| **Idempotent** | Property of operation | "DELETE is idempotent" |
| **Idempotency Key** | Deduplication token | `Idempotency-Key: abc-123` header |

```
Idempotent = the operation naturally repeats safely
Idempotency Key = mechanism to make non-idempotent operations safe
```

---

## 🔐 When to Use Each Strategy

### Strategy 1: Naturally Idempotent (GET, PUT, DELETE)

```
No action needed ✅
Just use HTTP correctly
```

### Strategy 2: Idempotency Key (POST)

```
Add header parameter
Track key in database
Return cached result if exists
```

Implementation in your API:

```python
# Client must send:
POST /todos HTTP/1.1
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000

# Server checks DB:
SELECT * FROM idempotency_keys WHERE key = '550e8400...'
```

### Strategy 3: Version Numbers (Optimistic Locking)

```
Prevent race conditions in updates
PATCH /todos/5
If-Match: "version-123"  # Only update if current version is 123
```

### Strategy 4: Unique Constraints (Database-level)

```python
# Your API has this:
title = Column(String(255), nullable=False, unique=True)

# Handles idempotency partially:
POST /todos { "title": "Buy milk" } → Success, created
POST /todos { "title": "Buy milk" } → 409 Conflict (UNIQUE constraint)

# But doesn't give same response (not true idempotency)
```

---

## 🚨 Common Idempotency Failures

### Failure 1: Partial Update Without PUT

```python
❌ BAD:
PATCH /users/5 { "increment_credits": 10 }

If retried:
Credits: 0 → 10 → 20 (not idempotent!)

✅ GOOD:
PATCH /users/5 { "set_credits_to": 100 }

If retried:
Credits: → 100 → 100 (idempotent!)
```

---

### Failure 2: Side Effects in CREATE

```python
❌ BAD:
def create_order(data):
    order = Order.create(data)
    send_confirmation_email()  # Side effect!
    return order

If retried:
- Creates 2 orders
- Sends 2 emails

✅ GOOD:
def create_order_with_idempotency(data, key):
    if exists(key):
        return get_cached(key)
    
    order = Order.create(data)
    cache(key, order)
    
    # Email sent only once per unique order
    send_confirmation_email()
    return order
```

---

### Failure 3: DELETE Returns Different Status

```python
❌ BAD:
DELETE /todos/5:
  First call: 204 No Content
  Retry: 404 Not Found
  
Different responses = not idempotent!

✅ GOOD:
Both calls return 204 No Content
Final state is identical
```

---

## 📈 Senior Backend Engineer Mindset

### The 5-Step Mental Model

When designing ANY API endpoint:

```
1. What HTTP method am I using?
   → GET? Already idempotent ✅
   → POST? Not idempotent ❌
   → PUT? Idempotent ✅
   → DELETE? Should be idempotent ✅

2. What are the side effects?
   → Database changes?
   → External API calls?
   → Sending emails?
   
3. Can this fail mid-execution?
   → Connection drops?
   → Server crashes?
   → Timeout?
   
4. If retried, what happens?
   → Same result? ✅
   → Different result? ❌
   → Duplicates? ❌
   → Corrupted data? ❌
   
5. How do I make it safe?
   → Use idempotent method?
   → Add idempotency key?
   → Database constraints?
   → Version numbers?
```

---

## 🧪 Testing Idempotency

### Simple Test Framework

```python
def assert_idempotent(endpoint, method, data, headers=None):
    """
    Verify that calling the same endpoint multiple times
    produces the same result.
    """
    responses = []
    db_states = []
    
    for i in range(3):
        # Make request
        response = client.request(method, endpoint, json=data, headers=headers)
        responses.append(response)
        
        # Check DB state
        state = capture_db_state()
        db_states.append(state)
    
    # All responses must be identical
    assert responses[0].status_code == responses[1].status_code
    assert responses[0].json() == responses[1].json()
    assert responses[1] == responses[2]
    
    # All DB states must be identical
    assert db_states[0] == db_states[1]
    assert db_states[1] == db_states[2]
    
    return True
```

### Usage

```python
# Test GET
assert_idempotent("GET", "/todos/5", None)  ✅

# Test PUT
assert_idempotent(
    "PUT",
    "/todos/5",
    {"title": "Updated", "done": True}
)  ✅

# Test DELETE
assert_idempotent("DELETE", "/todos/5", None)  ✅

# Test POST (before idempotency-key added)
assert_idempotent("POST", "/todos", {"title": "New"})  ❌ (fails - creates 3!)

# Test POST (after idempotency-key added)
assert_idempotent(
    "POST",
    "/todos",
    {"title": "New"},
    headers={"Idempotency-Key": "abc-123"}
)  ✅ (passes - cached!)
```

---

## 🏆 Final Wisdom

> "An idempotent API is one that doesn't surprise you with side effects when retried."

### Your TODO API Status

| Operation | Currently | Should Be |
|-----------|-----------|-----------|
| GET /todos/{id} | ✅ Idempotent | ✅ Keep as-is |
| PUT /todos/{id} | ✅ Idempotent | ✅ Keep as-is |
| DELETE /todos/{id} | ❌ 404 on retry | ✅ Fix: return 204 |
| POST /todos | ❌ Creates duplicates | ✅ Fix: add idempotency-key |

After fixing: **Your API will be production-ready for retries.**

