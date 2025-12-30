# Task Management Microservice

A complete microservice for managing tasks and todos in the CA application.

## Features

- **Task Management**: Create, read, update, and delete tasks
- **Todo Management**: Manage internal to-do items
- **Task Subtasks**: Add and manage subtasks for tasks
- **Time Tracking**: Start/stop timers and log manual time entries
- **Activity Logging**: Track all task changes and activities
- **Status Management**: Track task status (pending, in_progress, completed, hold)
- **Priority Levels**: P1 (Urgent) to P4 (Low)
- **Document Requests**: Configure document collection items per task

## API Endpoints

### Tasks
- `GET /tasks/` - List all tasks
- `POST /tasks/` - Create a new task
- `GET /tasks/{task_id}` - Get task details
- `PATCH /tasks/{task_id}` - Update a task
- `DELETE /tasks/{task_id}` - Delete a task
- `GET /tasks/{task_id}/history` - Get task activity history
- `POST /tasks/{task_id}/timer/start` - Start task timer
- `POST /tasks/{task_id}/timer/stop` - Stop task timer
- `POST /tasks/{task_id}/timer/manual` - Add manual time entry
- `POST /tasks/{task_id}/subtasks` - Add subtask
- `GET /tasks/{task_id}/subtasks` - Get all subtasks
- `PATCH /tasks/{task_id}/subtasks/{subtask_id}` - Update subtask
- `DELETE /tasks/{task_id}/subtasks/{subtask_id}` - Delete subtask

### Todos
- `GET /todos` - List all todos
- `POST /todos` - Create a new todo
- `GET /todos/{todo_id}` - Get todo details
- `PATCH /todos/{todo_id}` - Update a todo
- `DELETE /todos/{todo_id}` - Delete a todo

## Environment Variables

Required environment variables (set in `.env`):
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret key
- `ALGORITHM` - JWT algorithm (default: HS256)
- `API_URL` - Login service URL (default: http://login:8001)

## Running the Service

### Using Docker Compose
```bash
docker-compose up task
```

### Local Development
```bash
cd Task
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

## Database Models

- **Task**: Main task entity
- **Todo**: Internal to-do items
- **TaskSubtask**: Subtasks for tasks
- **TaskTimer**: Time tracking entries
- **ActivityLog**: Activity history

## Authentication

All endpoints require JWT Bearer token authentication via the `Authorization` header:
```
Authorization: Bearer <token>
```

Additionally, the `x-agency-id` header is required for multi-tenant support.

## Response Formats

The API returns data in the following formats:
- Single object: `{...}`
- List: `[{...}, {...}]`

The frontend is configured to handle both direct arrays and nested `{items: [...]}` formats.

