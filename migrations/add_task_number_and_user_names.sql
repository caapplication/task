-- Migration script to add task_number, created_by_name, and updated_by_name columns to tasks table
-- Run this script in pgAdmin or any PostgreSQL client

-- Add task_number column
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS task_number INTEGER;

-- Add created_by_name column
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS created_by_name VARCHAR(255);

-- Add updated_by_name column
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS updated_by_name VARCHAR(255);

-- Create unique index for task_number (per agency would be better, but unique globally for now)
-- Note: We'll need to populate task_number for existing tasks
CREATE UNIQUE INDEX IF NOT EXISTS ix_tasks_task_number 
ON tasks(task_number) 
WHERE task_number IS NOT NULL;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS ix_tasks_created_by_name 
ON tasks(created_by_name) 
WHERE created_by_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_tasks_updated_by_name 
ON tasks(updated_by_name) 
WHERE updated_by_name IS NOT NULL;

-- Populate task_number for existing tasks (sequential numbering)
DO $$
DECLARE
    task_rec RECORD;
    counter INTEGER := 1;
BEGIN
    FOR task_rec IN 
        SELECT id FROM tasks ORDER BY created_at ASC
    LOOP
        UPDATE tasks 
        SET task_number = counter 
        WHERE id = task_rec.id;
        counter := counter + 1;
    END LOOP;
END $$;

-- Verify the columns were added
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'tasks' 
    AND column_name IN ('task_number', 'created_by_name', 'updated_by_name');

