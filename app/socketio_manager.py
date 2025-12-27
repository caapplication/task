from socketio import AsyncServer
from typing import Dict, Set
import json

# Global Socket.IO server instance
sio: AsyncServer = None

# Store user connections: {user_id: {socket_id1, socket_id2, ...}}
user_connections: Dict[str, Set[str]] = {}

# Store task rooms: {task_id: {user_id1, user_id2, ...}}
task_rooms: Dict[str, Set[str]] = {}

def init_socketio(fastapi_app):
    """Initialize Socket.IO server"""
    global sio
    sio = AsyncServer(
        cors_allowed_origins="*",
        async_mode='asgi',
        logger=False,
        engineio_logger=False
    )
    return sio

def get_sio():
    """Get the global Socket.IO server instance"""
    return sio

async def emit_new_comment(task_id: str, comment_data: dict, sender_user_id: str):
    """Emit new comment event to all users watching this task except the sender"""
    if not sio:
        return
    
    # Get all users in the task room
    task_id_str = str(task_id)
    if task_id_str in task_rooms:
        for user_id in task_rooms[task_id_str]:
            # Don't send to the sender
            if user_id != sender_user_id:
                # Send to all socket connections for this user
                if user_id in user_connections:
                    for socket_id in user_connections[user_id]:
                        await sio.emit('new_comment', {
                            'task_id': task_id_str,
                            'comment': comment_data
                        }, room=socket_id)

async def emit_unread_update(task_id: str, user_id: str, has_unread: bool):
    """Emit unread message status update to a specific user"""
    if not sio:
        return
    
    if user_id in user_connections:
        for socket_id in user_connections[user_id]:
            await sio.emit('unread_update', {
                'task_id': str(task_id),
                'has_unread': has_unread
            }, room=socket_id)

async def emit_comment_read_receipt(task_id: str, comment_id: str, receipt_data: dict):
    """Emit read receipt update for a comment to all users watching this task"""
    if not sio:
        return
    
    task_id_str = str(task_id)
    if task_id_str in task_rooms:
        for user_id in task_rooms[task_id_str]:
            # Send to all socket connections for each user in the task room
            if user_id in user_connections:
                for socket_id in user_connections[user_id]:
                    await sio.emit('comment_read_receipt', {
                        'task_id': task_id_str,
                        'comment_id': str(comment_id),
                        'receipt': receipt_data
                    }, room=socket_id)

async def register_user_connection(user_id: str, socket_id: str):
    """Register a user's socket connection"""
    if user_id not in user_connections:
        user_connections[user_id] = set()
    user_connections[user_id].add(socket_id)

async def unregister_user_connection(user_id: str, socket_id: str):
    """Unregister a user's socket connection"""
    if user_id in user_connections:
        user_connections[user_id].discard(socket_id)
        if not user_connections[user_id]:
            del user_connections[user_id]

async def join_task_room(task_id: str, user_id: str):
    """Add user to task room"""
    task_id_str = str(task_id)
    if task_id_str not in task_rooms:
        task_rooms[task_id_str] = set()
    task_rooms[task_id_str].add(user_id)

async def leave_task_room(task_id: str, user_id: str):
    """Remove user from task room"""
    task_id_str = str(task_id)
    if task_id_str in task_rooms:
        task_rooms[task_id_str].discard(user_id)
        if not task_rooms[task_id_str]:
            del task_rooms[task_id_str]

