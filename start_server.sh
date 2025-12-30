#!/bin/bash
echo "Starting Task Management API Server..."
cd "$(dirname "$0")"
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload

