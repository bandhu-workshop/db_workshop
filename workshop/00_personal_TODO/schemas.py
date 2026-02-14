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
    created_at: str
    model_config = ConfigDict(from_attributes=True)

    # class Config:
    #     orm_mode = True
