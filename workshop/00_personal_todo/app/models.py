from app.core.database import Base
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    func,
)


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
