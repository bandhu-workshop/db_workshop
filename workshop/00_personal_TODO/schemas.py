from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TodoCreate(BaseModel):
    title: str
    description: str | None = None
    is_completed: bool = False


class TodoUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    is_completed: bool | None = None


class TodoResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    is_completed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
