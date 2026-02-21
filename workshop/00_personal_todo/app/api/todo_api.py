from app.core.database import get_db
from app.schemas import TodoCreate, TodoResponse, TodoUpdate
from app.services.todo_crud import (
    create_todo,
    delete_todo,
    get_todo,
    list_todos,
    restore_todo,
    soft_delete_todo,
    update_todo,
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
):
    return create_todo(session, todo)


@router.get("/", response_model=list[TodoResponse], status_code=200)
def list_todos_endpoint(
    session: Session = Depends(get_db),
):
    return list_todos(session)


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
            status_code=404,
            detail=f"TODO item not found or not deleted with id {todo_id}",
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
            status_code=404,
            detail=f"TODO item not found or not deleted with id {todo_id}",
        )
    return todo_item


# delete a TODO item by id
@router.delete(
    "/{todo_id}",
    status_code=204,
)
def soft_delete_todo_endpoint(
    todo_id: int,
    session: Session = Depends(get_db),
):
    result = soft_delete_todo(session, todo_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"TODO item not found or not deleted with id {todo_id}",
        )
    return None


# hard delete a TODO item by id
@router.delete(
    "/{todo_id}/hard",
    status_code=204,
)
def hard_delete_todo_endpoint(
    todo_id: int,
    session: Session = Depends(get_db),
):
    result = delete_todo(session, todo_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"TODO item not found or not deleted with id {todo_id}",
        )
    return None


# restore a soft-deleted TODO item by id
@router.post(
    "/{todo_id}/restore",
    response_model=TodoResponse,
    status_code=200,
)
def restore_todo_endpoint(
    todo_id: int,
    session: Session = Depends(get_db),
):
    todo_item = restore_todo(session, todo_id)
    if not todo_item:
        raise HTTPException(
            status_code=404,
            detail=f"TODO item not found or not deleted with id {todo_id}",
        )
    return todo_item
