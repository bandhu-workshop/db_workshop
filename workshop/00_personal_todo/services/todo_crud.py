"""
CRUD LAYER (Database Logic Only)

Architecture:
    API Layer  → FastAPI (routes, Depends, response_model)
    CRUD Layer → Pure DB operations (this file)
    DB Layer   → Engine, SessionLocal, Models

Rules:
✅ Accept SQLAlchemy Session explicitly.
❌ Never use Depends() here.
❌ Never open/close the session here.
❌ Return ORM models, NOT Pydantic schemas.
✅ Commit only for CREATE/UPDATE/DELETE.
❌ No commit for READ operations.
✅ Use model_dump(exclude_unset=True) for partial updates.
❓ How To Handle “Todo Not Found”?
    ❌ CRUD should NOT raise HTTPException. That belongs to API layer.
    ✅ CRUD should return None or False, and let the API layer (routes) handle the HTTP response.


Golden Thumb Rules:
1. API handles HTTP. CRUD handles database.
2. If FastAPI created the session, CRUD must not manage it.
3. CRUD returns models. Routes return schemas.
4. Reads don't commit. Writes always commit.
5. Clean separation today = scalable system tomorrow.
"""

from models import Todo, TodoIdempotency
from schemas import TodoCreate, TodoUpdate
from sqlalchemy.orm import Session


def get_todo_by_idempotency_key(session: Session, idempotency_key: str) -> Todo | None:
    """
    Check if we've already created a todo with this idempotency key.

    Returns the cached todo if key exists, None otherwise.
    """
    record = (
        session.query(TodoIdempotency)
        .filter(TodoIdempotency.idempotency_key == idempotency_key)
        .first()
    )

    if record:
        return session.get(Todo, record.todo_id)
    return None


def create_todo(session: Session, todo: TodoCreate) -> Todo:
    # create a new todo item
    todo_item = Todo(**todo.model_dump())
    session.add(todo_item)
    session.commit()
    session.refresh(todo_item)
    return todo_item


def create_todo_with_idempotency(
    session: Session,
    todo: TodoCreate,
    idempotency_key: str | None = None,
) -> tuple[Todo, bool]:
    """
    Create a todo with optional idempotency-key support.

    Args:
        session: SQLAlchemy session
        todo: Todo data to create
        idempotency_key: Optional idempotency key for deduplication

    Returns:
        tuple: (todo_item, is_new)
        - is_new=True: newly created todo
        - is_new=False: returned from cache (idempotency key match)

    Logic:
    1. If idempotency_key provided, check if we've seen it before
    2. If cached, return the cached todo (idempotent!)
    3. If not cached, create new todo
    4. Store idempotency key for future calls
    """
    # Step 1: Check cache if key provided
    if idempotency_key:
        cached_todo = get_todo_by_idempotency_key(session, idempotency_key)
        if cached_todo:
            return cached_todo, False  # Return cached, not new

    # Step 2: Create new todo (not in cache)
    todo_item = Todo(**todo.model_dump())
    session.add(todo_item)
    session.commit()
    session.refresh(todo_item)

    # Step 3: Store idempotency key if provided
    if idempotency_key:
        idempotency_record = TodoIdempotency(
            idempotency_key=idempotency_key,
            todo_id=todo_item.id,
        )
        session.add(idempotency_record)
        session.commit()

    return todo_item, True  # Newly created


def get_todo(session: Session, todo_id: int) -> Todo | None:
    # get a todo item by id
    # instead of
    #   `session.query(Todo).filter(Todo.id == todo_id).first()`,
    # we use
    #   `session.get(Todo, todo_id)`
    # which is more efficient and cleaner.
    #   - Cleaner
    #   - Faster
    #   - Primary-key optimized
    #   - More modern (SQLAlchemy 1.4+ / 2.0 style)

    return session.get(Todo, todo_id)


def update_todo(session: Session, todo_id: int, todo: TodoUpdate) -> Todo | None:
    # update a todo item by id
    todo_item = session.get(Todo, todo_id)
    if not todo_item:
        return None

    for key, value in todo.model_dump(exclude_unset=True).items():
        setattr(todo_item, key, value)

    session.commit()
    session.refresh(todo_item)
    return todo_item


def delete_todo(session: Session, todo_id: int) -> bool:
    # delete a todo item by id
    todo_item = session.get(Todo, todo_id)
    if not todo_item:
        return False

    session.delete(todo_item)
    session.commit()
    return True
