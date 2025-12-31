import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Enum, Date, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class TaskStatus(PyEnum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    hold = "hold"

class TaskPriority(PyEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_number = Column(Integer, nullable=True, unique=True, index=True)  # Sequential task number (T.ID)
    agency_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Null for todos
    service_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Null for todos
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.pending, nullable=False)  # Keep for backward compatibility
    stage_id = Column(UUID(as_uuid=True), ForeignKey("task_stages.id"), nullable=True, index=True)  # New custom stage
    priority = Column(Enum(TaskPriority), nullable=True)
    due_date = Column(Date, nullable=True)
    due_time = Column(String, nullable=True)  # Time for due date (HH:mm format)
    target_date = Column(Date, nullable=True)
    assigned_to = Column(UUID(as_uuid=True), nullable=True, index=True)
    tag_id = Column(UUID(as_uuid=True), nullable=True)
    document_request = Column(JSON, nullable=True)  # {enabled: bool, items: [{name: str, required: bool}]}
    checklist = Column(JSON, nullable=True)  # {enabled: bool, items: [{name: str, is_completed: bool, assigned_to: UUID}]}
    
    # Recurring task fields
    is_recurring = Column(Boolean, default=False, nullable=False)
    recurrence_frequency = Column(String, nullable=True)  # 'daily', 'weekly', 'monthly', 'quarterly', 'half_yearly', 'yearly'
    recurrence_time = Column(String, nullable=True)  # Time for daily recurrence (HH:mm format)
    recurrence_day_of_week = Column(Integer, nullable=True)  # 0-6 (Monday-Sunday) for weekly
    recurrence_date = Column(Date, nullable=True)  # Specific date for monthly/yearly
    recurrence_day_of_month = Column(Integer, nullable=True)  # 1-31 for quarterly/half_yearly
    recurrence_start_date = Column(Date, nullable=True)  # When recurrence starts
    
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_by_name = Column(String, nullable=True)  # Store creator's name
    created_by_role = Column(String, nullable=True)  # Store creator's role
    updated_by = Column(UUID(as_uuid=True), nullable=True)  # Track who last updated the task
    updated_by_name = Column(String, nullable=True)  # Store updater's name
    updated_by_role = Column(String, nullable=True)  # Store updater's role
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    stage = relationship("TaskStage", back_populates="tasks")
    subtasks = relationship("TaskSubtask", back_populates="task", cascade="all, delete-orphan", order_by="TaskSubtask.sort_order")
    timers = relationship("TaskTimer", back_populates="task", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="task", cascade="all, delete-orphan", order_by="ActivityLog.created_at.desc()")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan", order_by="TaskComment.created_at.asc()")
    collaborators = relationship("TaskCollaborator", back_populates="task", cascade="all, delete-orphan")
    closure_requests = relationship("TaskClosureRequest", back_populates="task", cascade="all, delete-orphan", order_by="TaskClosureRequest.created_at.desc()")

