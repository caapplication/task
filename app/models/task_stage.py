import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class TaskStage(Base):
    """Custom task stages that can be created by users"""
    __tablename__ = "task_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agency_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    color = Column(String, nullable=True)  # Hex color code for UI display
    sort_order = Column(Integer, default=0, nullable=False)  # For ordering stages
    is_default = Column(Boolean, default=False, nullable=False)  # Default stages that can't be deleted
    is_completed = Column(Boolean, default=False, nullable=False)  # Marks completion stage
    is_blocked = Column(Boolean, default=False, nullable=False)  # Marks blocked stage
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tasks = relationship("Task", back_populates="stage", cascade="all, delete-orphan")

