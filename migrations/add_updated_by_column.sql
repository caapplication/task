-- Migration script to add updated_by column to tasks table
-- Run this script in pgAdmin or any PostgreSQL client

-- Add updated_by column to tasks table
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS updated_by UUID;

-- Add index for better query performance
CREATE INDEX IF NOT EXISTS ix_tasks_updated_by 
ON tasks(updated_by) 
WHERE updated_by IS NOT NULL;

-- Verify the column was added (optional - just to check)
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'tasks' 
    AND column_name = 'updated_by';

