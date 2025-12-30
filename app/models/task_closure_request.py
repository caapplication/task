import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from app.database import Base

class ClosureRequestStatus(PyEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class TaskClosureRequest(Base):
    __tablename__ = "task_closure_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    requested_by = Column(UUID(as_uuid=True), nullable=False, index=True)  # User who requested closure
    status = Column(Enum(ClosureRequestStatus), default=ClosureRequestStatus.pending, nullable=False)
    reason = Column(Text, nullable=True)  # Optional reason for closure request
    reviewed_by = Column(UUID(as_uuid=True), nullable=True)  # User who approved/rejected
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    task = relationship("Task", back_populates="closure_requests")

