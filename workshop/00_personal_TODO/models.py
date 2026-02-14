from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)

from .database import Base


class Todo(Base):
    """
    Model for a TODO.
    Note: The class name is singular (Todo) while the table name is plural (todos). This is a common convention in SQLAlchemy models.
    """

    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    # Note: We use Text for description to allow for longer text, and we set nullable=True to make it optional.
    description = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TodoIdempotency(Base):
    """
    Stores idempotency keys to deduplicate POST requests.

    Why?
    - Client calls POST twice (network retry)
    - Without this, creates 2 todos → BAD
    - With this, returns same todo → GOOD (idempotent!)

    Design:
    - Each unique idempotency_key maps to one todo_id
    - If key seen before, return cached todo instead of creating new
    - Keys expire after 24 hours (optional cleanup)
    """

    __tablename__ = "todo_idempotency_keys"

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(50), unique=True, nullable=False, index=True)
    todo_id = Column(Integer, ForeignKey("todos.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
