from contextlib import asynccontextmanager

from api.todo_api import router as todo_router
from core.config import settings
from core.database import init_db, seed_db
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code here
    print("Starting up the application...")
    # init database (create tables)
    init_db()

    # seed database with initial data (development/learning only)
    # Set SEED_DB=true in .env or os.environ to enable seeding
    if settings.debug:  # or add a SEED_DB setting
        seed_db()

    yield
    # Shutdown code here
    print("Shutting down the application...")


app = FastAPI(app_name=settings.app_name, debug=settings.debug, lifespan=lifespan)


@app.get("/")
def health_check():
    return {"status": "ok"}


app.include_router(
    prefix="/todos",
    tags=["todos"],
    router=todo_router,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port, reload=settings.debug)
