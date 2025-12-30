-- Migration script to add user_name column to task_comment_reads table
-- Run this script in pgAdmin or any PostgreSQL client

-- Add user_name column (nullable for now to handle existing records)
ALTER TABLE task_comment_reads 
ADD COLUMN IF NOT EXISTS user_name VARCHAR(255);

-- Update existing records: You may want to run a separate script to populate
-- existing records with user names from the login service if needed

-- Verify column addition
SELECT 'user_name column added to task_comment_reads table successfully.' AS status;

