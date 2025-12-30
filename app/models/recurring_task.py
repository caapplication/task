import uuid
from datetime import datetime, date
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Enum, Date, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class RecurrenceFrequency(PyEnum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"

class RecurringTask(Base):
    __tablename__ = "recurring_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agency_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Task template fields (same as Task model)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    client_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    service_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    priority = Column(String, nullable=True)  # P1, P2, P3, P4
    assigned_to = Column(UUID(as_uuid=True), nullable=True, index=True)
    tag_id = Column(UUID(as_uuid=True), nullable=True)
    document_request = Column(JSON, nullable=True)
    
    # Recurrence configuration
    frequency = Column(Enum(RecurrenceFrequency), nullable=False)  # daily, weekly, monthly, yearly
    interval = Column(Integer, default=1, nullable=False)  # Every N days/weeks/months/years
    start_date = Column(Date, nullable=False)  # When to start creating tasks
    end_date = Column(Date, nullable=True)  # Optional end date for recurrence
    
    # Day of week/month configuration (for weekly/monthly)
    day_of_week = Column(Integer, nullable=True)  # 0-6 (Monday-Sunday) for weekly
    day_of_month = Column(Integer, nullable=True)  # 1-31 for monthly
    week_of_month = Column(Integer, nullable=True)  # 1-4 for monthly (first, second, third, fourth week)
    
    # Due date configuration
    due_date_offset = Column(Integer, default=0, nullable=False)  # Days to add to creation date for due_date
    target_date_offset = Column(Integer, nullable=True)  # Days to add to creation date for target_date
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_created_at = Column(DateTime(timezone=True), nullable=True)  # Last time a task was created from this template
    
    # Relationship to track created tasks (optional, for reference)
    # Note: We don't store a direct relationship since tasks are independent entities

