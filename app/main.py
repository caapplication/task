from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from socketio import ASGIApp

from app.database import get_db
from app.routers import tasks, todos, recurring_tasks, scheduler, task_stages, task_comments
from app.socketio_manager import init_socketio

fastapi_app = FastAPI(title="Task Management API", version="1.0.0")

# Initialize Socket.IO
socketio_server = init_socketio(fastapi_app)

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

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@fastapi_app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    from app.database import SessionLocal
    request.state.db = SessionLocal()
    try:
        response = await call_next(request)
    finally:
        request.state.db.close()
    return response

# Include routers
fastapi_app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
fastapi_app.include_router(task_stages.router, prefix="/task-stages", tags=["task-stages"])
fastapi_app.include_router(task_comments.router, tags=["task-comments"])
fastapi_app.include_router(todos.router, prefix="/todos", tags=["todos"])
fastapi_app.include_router(recurring_tasks.router, tags=["recurring-tasks"])
fastapi_app.include_router(scheduler.router, tags=["scheduler"])

@fastapi_app.get("/")
def read_root():
    return {"message": "Welcome to the Task Management API", "version": "1.0.0"}

@fastapi_app.get("/health")
def health_check():
    return {"status": "healthy"}

# Socket.IO event handlers
@socketio_server.on('connect')
async def handle_connect(sid, environ, auth):
    """Handle client connection"""
    if auth and 'user_id' in auth:
        user_id = auth['user_id']
        from app.socketio_manager import register_user_connection
        await register_user_connection(user_id, sid)
        await socketio_server.emit('connected', {'status': 'ok'}, room=sid)
        return True
    return False

@socketio_server.on('disconnect')
async def handle_disconnect(sid):
    """Handle client disconnection"""
    from app.socketio_manager import unregister_user_connection, user_connections
    # Find user_id for this socket
    for user_id, sockets in user_connections.items():
        if sid in sockets:
            await unregister_user_connection(user_id, sid)
            break

@socketio_server.on('join_task')
async def handle_join_task(sid, data):
    """Handle user joining a task room"""
    if 'task_id' in data and 'user_id' in data:
        from app.socketio_manager import join_task_room
        await join_task_room(data['task_id'], data['user_id'])
        await socketio_server.enter_room(sid, f"task_{data['task_id']}")

@socketio_server.on('leave_task')
async def handle_leave_task(sid, data):
    """Handle user leaving a task room"""
    if 'task_id' in data and 'user_id' in data:
        from app.socketio_manager import leave_task_room
        await leave_task_room(data['task_id'], data['user_id'])
        await socketio_server.leave_room(sid, f"task_{data['task_id']}")

# Wrap FastAPI app with Socket.IO
app = ASGIApp(socketio_server, fastapi_app)

