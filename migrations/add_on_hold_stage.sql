-- Migration script to add "On Hold" stage to existing agencies
-- Run this script in pgAdmin or any PostgreSQL client
-- This script adds the "On Hold" stage to all agencies that don't already have it

-- Step 1: Update sort_order for existing default stages
-- Update "Complete" stage sort_order to 4 (if it exists and is default)
UPDATE task_stages
SET sort_order = 4, updated_at = CURRENT_TIMESTAMP
WHERE name = 'Complete' 
  AND is_default = true 
  AND sort_order != 4;

-- Update "Blocked" stage sort_order to 5 (if it exists and is default)
UPDATE task_stages
SET sort_order = 5, updated_at = CURRENT_TIMESTAMP
WHERE name = 'Blocked' 
  AND is_default = true 
  AND sort_order != 5;

-- Step 2: Add "On Hold" stage to agencies that don't have it
-- For each agency, find if "On Hold" stage exists, if not, create it
-- We'll use the first user from each agency as created_by (or a system user if available)

-- Insert "On Hold" stage for each agency that doesn't have it
-- Using the created_by from existing default stages for each agency
INSERT INTO task_stages (
    id,
    agency_id,
    name,
    description,
    color,
    sort_order,
    is_default,
    is_completed,
    is_blocked,
    created_by,
    created_at,
    updated_at
)
SELECT 
    gen_random_uuid() as id,
    agency_id,
    'On Hold' as name,
    'Tasks that are temporarily paused' as description,
    '#fbbf24' as color,
    3 as sort_order,
    true as is_default,
    false as is_completed,
    false as is_blocked,
    -- Use the created_by from the first default stage for this agency
    (SELECT created_by FROM task_stages ts2 
     WHERE ts2.agency_id = agencies.agency_id 
     AND ts2.is_default = true 
     ORDER BY ts2.created_at ASC 
     LIMIT 1) as created_by,
    CURRENT_TIMESTAMP as created_at,
    CURRENT_TIMESTAMP as updated_at
FROM (
    -- Get distinct agency_ids that have stages but don't have "On Hold"
    SELECT DISTINCT ts.agency_id
    FROM task_stages ts
    WHERE NOT EXISTS (
        SELECT 1 
        FROM task_stages ts2 
        WHERE ts2.agency_id = ts.agency_id 
        AND ts2.name = 'On Hold'
    )
) as agencies
WHERE EXISTS (
    -- Only add if agency has at least one stage (meaning it's an active agency)
    SELECT 1 FROM task_stages WHERE task_stages.agency_id = agencies.agency_id LIMIT 1
);

-- Step 3: Verify the migration
-- Check how many "On Hold" stages were created
SELECT 
    COUNT(*) as on_hold_stages_created,
    COUNT(DISTINCT agency_id) as agencies_updated
FROM task_stages
WHERE name = 'On Hold' AND is_default = true;

-- Show all default stages for verification
SELECT 
    agency_id,
    name,
    sort_order,
    color,
    is_default,
    is_completed,
    is_blocked
FROM task_stages
WHERE is_default = true
ORDER BY agency_id, sort_order;

