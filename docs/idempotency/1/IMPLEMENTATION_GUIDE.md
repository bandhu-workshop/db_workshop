# 🛠️ Implementation Guide: Making Your API Idempotent

---

## ✅ QUICK FIX #1: Make DELETE Truly Idempotent (2 min)

### Problem

```python
# Current: Returns error on retry
DELETE /todos/5 (first call)  → 204 ✅
DELETE /todos/5 (retry)      → 404 ❌
```

### Solution

Change [todo_api.py](todo_api.py) line 61-69:

**From:**
```python
def delete_todo_endpoint(
    todo_id: int,
    session: Session = Depends(get_db),
):
    success = delete_todo(session, todo_id)
    if not success:
        raise HTTPException(
            status_code=404, detail=f"TODO item not found with id {todo_id}"
        )
    return None
```

**To:**
```python
def delete_todo_endpoint(
    todo_id: int,
    session: Session = Depends(get_db),
):
    delete_todo(session, todo_id)  # Call but ignore result
    return None  # Always 204: idempotent ✅
```

### Why This Works

- **1st DELETE /todos/5** → Todo deleted → 204 ✅
- **2nd DELETE /todos/5** → Already gone, but return 204 anyway ✅
- **3rd DELETE /todos/5** → Still 204 ✅

**State after all calls**: Todo doesn't exist (idempotent!)

---

## 🔐 MEDIUM FIX #2: Add Idempotency-Key to POST

### Step 1: Add Idempotency Model

Create tracker table:

```python
# In models.py, add:

class TodoIdempotency(Base):
    """
    Stores idempotency keys to prevent duplicate POST requests.
    
    Why?
    - Client calls POST twice (network retry)
    - Without this, creates 2 todos → BAD
    - With this, returns same todo → GOOD
    """
    
    __tablename__ = "todo_idempotency_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(50), unique=True, nullable=False, index=True)
    todo_id = Column(Integer, ForeignKey("todos.id"), nullable=False)
    
    # Track when key was used
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Expire old keys after 24 hours (optional)
    # Use a background job to clean these up
```

### Step 2: Modify CRUD Layer

Update [todo_crud.py](todo_crud.py):

```python
from uuid import UUID
from datetime import datetime, timedelta

def get_idempotent_todo(session: Session, idempotency_key: str) -> Todo | None:
    """Check if we've already created a todo with this key."""
    from .models import TodoIdempotency
    
    record = session.query(TodoIdempotency).filter(
        TodoIdempotency.idempotency_key == idempotency_key
    ).first()
    
    if record:
        return session.get(Todo, record.todo_id)
    return None


def create_todo_with_idempotency(
    session: Session,
    todo: TodoCreate,
    idempotency_key: str | None = None,
) -> tuple[Todo, bool]:
    """
    Create a todo with idempotency.
    
    Returns:
        (todo_item, is_new)
        - is_new=True: newly created
        - is_new=False: returned from cache
    """
    from .models import TodoIdempotency
    
    # If idempotency key provided, check cache
    if idempotency_key:
        cached_todo = get_idempotent_todo(session, idempotency_key)
        if cached_todo:
            return cached_todo, False  # Return cached
    
    # Create new todo
    todo_item = Todo(**todo.model_dump())
    session.add(todo_item)
    try:
        session.commit()
        session.refresh(todo_item)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"A TODO with this title `{todo.title}` already exists.",
        )
    
    # Store idempotency key if provided
    if idempotency_key:
        idempotency_record = TodoIdempotency(
            idempotency_key=idempotency_key,
            todo_id=todo_item.id,
        )
        session.add(idempotency_record)
        session.commit()
    
    return todo_item, True  # Newly created
```

### Step 3: Update API Endpoint

In [todo_api.py](todo_api.py):

```python
from uuid import UUID

@router.post(
    "/",
    response_model=TodoResponse,
    status_code=201,
)
def create_todo_endpoint(
    todo: TodoCreate,
    idempotency_key: str | None = Header(None),  # NEW: Optional header
    session: Session = Depends(get_db),
):
    # NEW: Use idempotency-aware function
    todo_item, is_new = create_todo_with_idempotency(
        session,
        todo,
        idempotency_key=idempotency_key,
    )
    
    # Return 201 only if newly created, else 200
    if is_new:
        return todo_item
    else:
        # Optional: Return 200 instead of 201 to indicate cached
        return todo_item
```

### How to Test It

```bash
# First call - creates todo
curl -X POST http://localhost:8000/todos \
  -H "Idempotency-Key: abc-123" \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy milk"}'
# Response: 201 Created, todo_id: 5

# Retry with same key
curl -X POST http://localhost:8000/todos \
  -H "Idempotency-Key: abc-123" \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy milk"}'
# Response: 201 Created (or 200), todo_id: 5 (SAME! ✅)

# Different key = different todo
curl -X POST http://localhost:8000/todos \
  -H "Idempotency-Key: xyz-789" \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy milk"}'
# Response: 201 Created, todo_id: 6 (NEW! ✅)
```

---

## 📝 Implementation Checklist

### Phase 1 (Immediate - 5 min)

- [ ] **Fix DELETE** → Remove 404 error check in todo_api.py
- [ ] Test: `DELETE /todos/99` twice → both should be 204

### Phase 2 (Next - 30 min)

- [ ] Add `TodoIdempotency` model to models.py
- [ ] Add `create_todo_with_idempotency()` function to todo_crud.py
- [ ] Update POST endpoint in todo_api.py
- [ ] Test with curl (see above)

### Phase 3 (Polish - optional)

- [ ] Add validation: reject requests without idempotency-key header
- [ ] Add cleanup: remove keys older than 24 hours
- [ ] Add logging: track cache hits vs misses
- [ ] Add metrics: monitor duplicate detection

---

## 🧪 Test Cases (After Implementation)

### DELETE Idempotency Test

```python
def test_delete_idempotent(client, session):
    # Create a todo
    response = client.post("/todos", json={"title": "Test"})
    todo_id = response.json()["id"]
    
    # Delete it
    resp1 = client.delete(f"/todos/{todo_id}")
    assert resp1.status_code == 204
    
    # Delete again (should still be 204, not 404!)
    resp2 = client.delete(f"/todos/{todo_id}")
    assert resp2.status_code == 204  ✅ IDEMPOTENT
    
    # Verify todo is gone
    resp3 = client.get(f"/todos/{todo_id}")
    assert resp3.status_code == 404
```

### POST Idempotency Test

```python
def test_post_idempotent(client, session):
    # First POST
    resp1 = client.post(
        "/todos",
        json={"title": "Buy milk"},
        headers={"Idempotency-Key": "abc-123"}
    )
    assert resp1.status_code == 201
    todo_id_1 = resp1.json()["id"]
    
    # Retry with same key
    resp2 = client.post(
        "/todos",
        json={"title": "Buy milk"},
        headers={"Idempotency-Key": "abc-123"}
    )
    assert resp2.status_code == 201
    todo_id_2 = resp2.json()["id"]
    
    # Should be same todo!
    assert todo_id_1 == todo_id_2  ✅ IDEMPOTENT
    
    # Count todos by title
    todos = session.query(Todo).filter(Todo.title == "Buy milk").all()
    assert len(todos) == 1  # Only 1, not 2!
```

---

## 🚀 Next Steps After Implementation

1. **Add to documentation**: Document the `Idempotency-Key` header
2. **Client guidance**: Tell users to use `uuid4()` for idempotency-key
3. **Monitoring**: Alert if same key used with different data
4. **Cleanup**: Add scheduled job to remove old idempotency records
5. **Versioning**: After this works, add version-based PUT locking

