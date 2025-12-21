from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from fastapi import Request
from app.dependencies import get_current_user, get_current_agency
from app.crud import crud_todo
from app.schemas.todo import TodoCreate, TodoUpdate, Todo

router = APIRouter()

def get_db(request: Request):
    return request.state.db

@router.post("/", response_model=Todo, status_code=status.HTTP_201_CREATED)
def create_todo(
    todo: TodoCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    return crud_todo.create_todo(
        db=db,
        todo=todo,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
    )

@router.get("/", response_model=List[Todo])
def list_todos(
    assigned_to: Optional[UUID] = Query(None),
    is_completed: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    todos = crud_todo.get_todos_by_agency(
        db=db,
        agency_id=current_agency["id"],
        assigned_to=assigned_to,
        is_completed=is_completed,
        skip=skip,
        limit=limit
    )
    # Return as list directly (frontend handles both array and {items: []} format)
    return todos

@router.get("/{todo_id}", response_model=Todo)
def get_todo(
    todo_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    todo = crud_todo.get_todo(db=db, todo_id=todo_id, agency_id=current_agency["id"])
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo

@router.patch("/{todo_id}", response_model=Todo)
def update_todo(
    todo_id: UUID,
    todo_update: TodoUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    todo = crud_todo.update_todo(
        db=db,
        todo_id=todo_id,
        todo_update=todo_update,
        agency_id=current_agency["id"]
    )
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo

@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    success = crud_todo.delete_todo(
        db=db,
        todo_id=todo_id,
        agency_id=current_agency["id"]
    )
    if not success:
        raise HTTPException(status_code=404, detail="Todo not found")

