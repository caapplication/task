-- SQL script to add the checklist column to the tasks table
-- Run this in your PostgreSQL database

ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS checklist JSON;

-- Verify the column was added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'tasks' AND column_name = 'checklist';

