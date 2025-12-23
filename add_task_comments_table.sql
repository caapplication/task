-- SQL script to create the task_comments table
-- This script is for PostgreSQL.

DO $$
BEGIN
    -- Check if the 'task_comments' table already exists
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = current_schema()
        AND table_name = 'task_comments'
    ) THEN
        -- Create the task_comments table
        CREATE TABLE task_comments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id UUID NOT NULL,
            user_id UUID NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_task_comments_task_id
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        );
        
        -- Create indexes for better query performance
        CREATE INDEX idx_task_comments_task_id ON task_comments(task_id);
        CREATE INDEX idx_task_comments_user_id ON task_comments(user_id);
        CREATE INDEX idx_task_comments_created_at ON task_comments(created_at);
        
        RAISE NOTICE 'Table "task_comments" created successfully with indexes.';
    ELSE
        RAISE NOTICE 'Table "task_comments" already exists.';
    END IF;
END
$$;

-- Verify the table was created
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'task_comments'
ORDER BY ordinal_position;

