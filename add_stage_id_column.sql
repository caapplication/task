-- SQL script to add the stage_id column to the tasks table
-- This script is for PostgreSQL.

DO $$
BEGIN
    -- Check if the 'stage_id' column already exists in the 'tasks' table
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
        AND table_name = 'tasks'
        AND column_name = 'stage_id'
    ) THEN
        -- If the column does not exist, add it
        ALTER TABLE tasks
        ADD COLUMN stage_id UUID;
        
        -- Add foreign key constraint to task_stages table
        ALTER TABLE tasks
        ADD CONSTRAINT fk_tasks_stage_id
        FOREIGN KEY (stage_id) REFERENCES task_stages(id);
        
        -- Add index for better query performance
        CREATE INDEX IF NOT EXISTS idx_tasks_stage_id ON tasks(stage_id);
        
        RAISE NOTICE 'Column "stage_id" added to table "tasks" with foreign key constraint and index.';
    ELSE
        RAISE NOTICE 'Column "stage_id" already exists in table "tasks".';
    END IF;
END
$$;

-- Verify the column was added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'tasks' AND column_name = 'stage_id';

