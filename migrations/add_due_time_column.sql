-- Migration script to add due_time column to tasks table
-- Run this script in pgAdmin or any PostgreSQL client

-- Add due_time column
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS due_time VARCHAR(10);

-- Verify the column was added
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'tasks' 
    AND column_name = 'due_time';

