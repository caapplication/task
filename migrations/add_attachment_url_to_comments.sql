-- Migration script to add attachment columns to task_comments table
-- Run this script in pgAdmin or any PostgreSQL client

-- Add attachment_url column
ALTER TABLE task_comments 
ADD COLUMN IF NOT EXISTS attachment_url VARCHAR(500);

-- Add attachment_name column
ALTER TABLE task_comments 
ADD COLUMN IF NOT EXISTS attachment_name VARCHAR(255);

-- Add attachment_type column
ALTER TABLE task_comments 
ADD COLUMN IF NOT EXISTS attachment_type VARCHAR(100);

-- Make message column nullable (to allow comments with only attachments)
ALTER TABLE task_comments 
ALTER COLUMN message DROP NOT NULL;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS ix_task_comments_attachment_url 
ON task_comments(attachment_url) 
WHERE attachment_url IS NOT NULL;

-- Verify the columns were updated
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'task_comments' 
    AND column_name IN ('message', 'attachment_url', 'attachment_name', 'attachment_type');


