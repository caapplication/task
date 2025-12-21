import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Enum, Date, Text
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
    agency_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Null for todos
    service_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Null for todos
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.pending, nullable=False)
    priority = Column(Enum(TaskPriority), nullable=True)
    due_date = Column(Date, nullable=True)
    target_date = Column(Date, nullable=True)
    assigned_to = Column(UUID(as_uuid=True), nullable=True, index=True)
    tag_id = Column(UUID(as_uuid=True), nullable=True)
    document_request = Column(JSON, nullable=True)  # {enabled: bool, items: [{name: str, required: bool}]}
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subtasks = relationship("TaskSubtask", back_populates="task", cascade="all, delete-orphan", order_by="TaskSubtask.sort_order")
    timers = relationship("TaskTimer", back_populates="task", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="task", cascade="all, delete-orphan", order_by="ActivityLog.created_at.desc()")

