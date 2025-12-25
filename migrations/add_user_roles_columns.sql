-- Migration script to add created_by_role and updated_by_role columns to tasks table
-- Run this script in pgAdmin or any PostgreSQL client

-- Add created_by_role column
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS created_by_role VARCHAR(50);

-- Add updated_by_role column
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS updated_by_role VARCHAR(50);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS ix_tasks_created_by_role 
ON tasks(created_by_role) 
WHERE created_by_role IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_tasks_updated_by_role 
ON tasks(updated_by_role) 
WHERE updated_by_role IS NOT NULL;

-- Verify the columns were added
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'tasks' 
    AND column_name IN ('created_by_role', 'updated_by_role');

