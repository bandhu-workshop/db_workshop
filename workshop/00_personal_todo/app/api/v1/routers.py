from app.api.v1.endpoints.todo import router as todo_router
from fastapi import APIRouter

router = APIRouter()
router.include_router(todo_router, prefix="/todos", tags=["todos"])
