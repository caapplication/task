import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class TaskTimer(Base):
    __tablename__ = "task_timers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, default=0)  # Calculated duration
    is_active = Column(Boolean, default=True)
    notes = Column(String, nullable=True)  # For manual time entries
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    task = relationship("Task", back_populates="timers")

