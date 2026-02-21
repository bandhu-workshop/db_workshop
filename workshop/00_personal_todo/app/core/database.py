from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create the SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,
)

# Create sessionmaker factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for our models
Base = declarative_base()


# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# init db
def init_db():
    # important: ensures models are registered before creating tables
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    print("✅ Database tables initialized")


# seed_db() - ONLY loads data
def seed_db():
    import json
    from pathlib import Path

    import app.models  # noqa: F401

    session = SessionLocal()
    try:
        if session.query(app.models.Todo).count() == 0:
            seed_file = Path(__file__).parent.parent.parent / "seed_data.json"
            if seed_file.exists():
                with open(seed_file, "r") as f:
                    todos_data = json.load(f)

                for todo_data in todos_data:
                    todo = app.models.Todo(**todo_data)
                    session.add(todo)

                session.commit()
                print(f"✅ Loaded {len(todos_data)} todos")
    finally:
        session.close()
