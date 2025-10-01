-- FileManager Bot Database Initialization
-- This script runs when the PostgreSQL container is first created

-- Create the filemanager database if it doesn't exist
-- (This is handled by POSTGRES_DB environment variable)

-- Set timezone
SET timezone = 'UTC';

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create custom types if needed
-- DO $$ BEGIN
--     CREATE TYPE file_status AS ENUM ('active', 'deleted', 'archived');
-- EXCEPTION
--     WHEN duplicate_object THEN null;
-- END $$;

-- Create indexes for better performance
-- These will be created after tables are defined by Alembic

-- Set default configuration for the FileManager bot
-- Optimize for JSON operations if using JSON fields
SET work_mem = '256MB';

-- Log the initialization
DO $$
BEGIN
    RAISE NOTICE 'FileManager database initialized at %', NOW();
END $$;