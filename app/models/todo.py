import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class Todo(Base):
    __tablename__ = "todos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agency_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String, nullable=False)
    details = Column(String, nullable=True)
    assigned_to = Column(UUID(as_uuid=True), nullable=True, index=True)
    due_date = Column(Date, nullable=True)
    repeat_interval = Column(String, nullable=True)  # 'day', 'week', 'month', 'year'
    repeat_every = Column(Integer, nullable=True)  # Every N intervals
    is_completed = Column(Boolean, default=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

