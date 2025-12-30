"""
Scheduler endpoint for manually triggering recurring task creation.
In production, this should be called by a cron job or task scheduler.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user, get_current_agency, require_role
from app.services.recurring_task_scheduler import create_tasks_from_recurring_templates

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

@router.post("/create-recurring-tasks")
def trigger_recurring_task_creation(
    check_date: Optional[str] = None,  # YYYY-MM-DD format
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
    _: dict = Depends(require_role(["CA_ACCOUNTANT", "CA_TEAM"])),
):
    """
    Manually trigger creation of tasks from recurring templates.
    If check_date is not provided, uses today's date.
    This endpoint should typically be called by a cron job or scheduler.
    """
    try:
        if check_date:
            check_date_obj = date.fromisoformat(check_date)
        else:
            check_date_obj = date.today()
        
        tasks_created = create_tasks_from_recurring_templates(check_date_obj)
        
        return {
            "message": f"Recurring task scheduler completed",
            "check_date": str(check_date_obj),
            "tasks_created": tasks_created
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating recurring tasks: {str(e)}")

