-- Migration script to create task_comment_reads table for tracking unread messages
-- Run this script in pgAdmin or any PostgreSQL client

CREATE TABLE IF NOT EXISTS task_comment_reads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    comment_id UUID NOT NULL,
    user_id UUID NOT NULL,
    read_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_task_comment_reads_comment_id FOREIGN KEY (comment_id) REFERENCES task_comments(id) ON DELETE CASCADE,
    CONSTRAINT uq_task_comment_read UNIQUE (comment_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_task_comment_reads_comment_id ON task_comment_reads (comment_id);
CREATE INDEX IF NOT EXISTS ix_task_comment_reads_user_id ON task_comment_reads (user_id);

-- Verify table creation
SELECT 'task_comment_reads table created successfully.' AS status;

