from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers import tasks, todos, recurring_tasks, scheduler, task_stages, task_comments

app = FastAPI(title="Task Management API", version="1.0.0")

# Configure CORS
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://app.fynivo.in",
    "https://login-api.fynivo.in",
    "https://finance-api.fynivo.in",
    "https://client-api.fynivo.in",
    "https://services-api.fynivo.in",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    from app.database import SessionLocal
    request.state.db = SessionLocal()
    try:
        response = await call_next(request)
    finally:
        request.state.db.close()
    return response

# Include routers
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(task_stages.router, prefix="/task-stages", tags=["task-stages"])
app.include_router(task_comments.router, tags=["task-comments"])
app.include_router(todos.router, prefix="/todos", tags=["todos"])
app.include_router(recurring_tasks.router, tags=["recurring-tasks"])
app.include_router(scheduler.router, tags=["scheduler"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Task Management API", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

