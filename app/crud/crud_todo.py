from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from datetime import datetime
from typing import List, Optional

from app.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoUpdate

def create_todo(db: Session, todo: TodoCreate, agency_id: UUID, user_id: UUID) -> Todo:
    todo_data = todo.model_dump()
    db_todo = Todo(
        **todo_data,
        agency_id=agency_id,
        created_by=user_id,
        is_completed=False
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo

def get_todo(db: Session, todo_id: UUID, agency_id: UUID) -> Optional[Todo]:
    return db.query(Todo).filter(
        and_(Todo.id == todo_id, Todo.agency_id == agency_id)
    ).first()

def get_todos_by_agency(
    db: Session,
    agency_id: UUID,
    assigned_to: Optional[UUID] = None,
    is_completed: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Todo]:
    query = db.query(Todo).filter(Todo.agency_id == agency_id)
    
    if assigned_to:
        query = query.filter(Todo.assigned_to == assigned_to)
    if is_completed is not None:
        query = query.filter(Todo.is_completed == is_completed)
    
    return query.order_by(Todo.created_at.desc()).offset(skip).limit(limit).all()

def update_todo(
    db: Session,
    todo_id: UUID,
    todo_update: TodoUpdate,
    agency_id: UUID
) -> Optional[Todo]:
    db_todo = get_todo(db, todo_id, agency_id)
    if not db_todo:
        return None
    
    update_data = todo_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(db_todo, key, value)
    
    db_todo.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_todo)
    return db_todo

def delete_todo(db: Session, todo_id: UUID, agency_id: UUID) -> bool:
    db_todo = get_todo(db, todo_id, agency_id)
    if not db_todo:
        return False
    
    db.delete(db_todo)
    db.commit()
    return True

