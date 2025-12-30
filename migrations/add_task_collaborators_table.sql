-- Migration script to create task_collaborators table
-- Run this script in pgAdmin or any PostgreSQL client

-- Create task_collaborators table
CREATE TABLE IF NOT EXISTS task_collaborators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    added_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_task_collaborator UNIQUE (task_id, user_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS ix_task_collaborators_task_id ON task_collaborators(task_id);
CREATE INDEX IF NOT EXISTS ix_task_collaborators_user_id ON task_collaborators(user_id);
CREATE INDEX IF NOT EXISTS ix_task_collaborators_added_by ON task_collaborators(added_by);

-- Verify the table was created
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'task_collaborators' 
ORDER BY ordinal_position;

