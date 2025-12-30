import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class ActivityLog(Base):
    __tablename__ = "task_activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String, nullable=False)  # e.g., "Task created", "Status changed", "Timer started"
    details = Column(Text, nullable=True)
    event_type = Column(String, nullable=True)  # e.g., "task_created", "status_changed", "timer_started"
    from_value = Column(JSON, nullable=True)  # Previous value for changes
    to_value = Column(JSON, nullable=True)  # New value for changes
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    task = relationship("Task", back_populates="activity_logs")

