from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .schemas import TodoCreate, TodoResponse, TodoUpdate
from .todo_crud import create_todo_with_idempotency, delete_todo, get_todo, update_todo

router = APIRouter()


# create a new TODO item
@router.post(
    "/",
    response_model=TodoResponse,
    status_code=201,
)
def create_todo_endpoint(
    todo: TodoCreate,
    session: Session = Depends(get_db),
    idempotency_key: str | None = Header(None),
):
    todo_item, is_new = create_todo_with_idempotency(
        session, todo, idempotency_key=idempotency_key
    )
    return todo_item


# get a TODO item by id
@router.get(
    "/{todo_id}",
    response_model=TodoResponse,
    status_code=200,
)
def get_todo_endpoint(
    todo_id: int,
    session: Session = Depends(get_db),
):
    todo_item = get_todo(session, todo_id)
    if not todo_item:
        raise HTTPException(
            status_code=404, detail=f"TODO item not found with id {todo_id}"
        )
    return todo_item


# update a TODO item by id
@router.put(
    "/{todo_id}",
    response_model=TodoResponse,
    status_code=200,
)
def update_todo_endpoint(
    todo_id: int,
    todo: TodoUpdate,
    session: Session = Depends(get_db),
):
    todo_item = update_todo(session, todo_id, todo)
    if not todo_item:
        raise HTTPException(
            status_code=404, detail=f"TODO item not found with id {todo_id}"
        )
    return todo_item


# delete a TODO item by id
@router.delete(
    "/{todo_id}",
    status_code=204,
)
def delete_todo_endpoint(
    todo_id: int,
    session: Session = Depends(get_db),
):
    delete_todo(session, todo_id)
    return None
