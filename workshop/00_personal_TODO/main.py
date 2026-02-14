from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code here
    print("Starting up the application...")
    # init database (create tables)
    init_db()

    yield
    # Shutdown code here
    print("Shutting down the application...")


app = FastAPI(app_name=settings.app_name, debug=settings.debug, lifespan=lifespan)


@app.get("/")
def read_root():
    return {"Hello": "World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port, reload=settings.debug)
