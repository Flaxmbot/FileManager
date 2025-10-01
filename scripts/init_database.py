#!/usr/bin/env python3
"""
PostgreSQL Database Initialization Script

This script automates the setup and initialization of PostgreSQL databases
for different environments (development, staging, production).

Features:
- Database creation and user management
- Schema initialization and migrations
- Environment-specific configurations
- Backup and restore capabilities
- Connection testing and validation

Usage:
    python scripts/init_database.py --environment development
    python scripts/init_database.py --create-user --database-name mydb
"""

import argparse
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import asyncpg
from asyncpg import Connection


class DatabaseManager:
    """PostgreSQL database management"""

    def __init__(self, host: str = "localhost", port: int = 5432, admin_user: str = "postgres"):
        self.host = host
        self.port = port
        self.admin_user = admin_user
        self.admin_password = os.getenv("POSTGRES_PASSWORD", "postgres")

    async def create_connection(self, database: str = "postgres", **kwargs) -> Connection:
        """Create database connection"""
        return await asyncpg.connect(
            host=self.host,
            port=self.port,
            user=self.admin_user,
            password=self.admin_password,
            database=database,
            **kwargs
        )

    async def test_connection(self) -> bool:
        """Test PostgreSQL connection"""
        try:
            conn = await self.create_connection()
            await conn.close()
            print(f"✅ Connected to PostgreSQL at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"❌ Cannot connect to PostgreSQL: {e}")
            return False

    async def create_database(self, db_name: str, owner: str) -> bool:
        """Create new database"""
        try:
            conn = await self.create_connection()

            # Check if database exists
            result = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                db_name
            )

            if result:
                print(f"⚠️ Database '{db_name}' already exists")
                await conn.close()
                return True

            # Create database
            await conn.execute(f"CREATE DATABASE {db_name} OWNER {owner}")
            print(f"✅ Created database '{db_name}' with owner '{owner}'")

            await conn.close()
            return True

        except Exception as e:
            print(f"❌ Failed to create database '{db_name}': {e}")
            return False

    async def create_user(self, username: str, password: str, databases: List[str] = None) -> bool:
        """Create database user"""
        try:
            conn = await self.create_connection()

            # Check if user exists
            result = await conn.fetchval(
                "SELECT 1 FROM pg_user WHERE usename = $1",
                username
            )

            if result:
                print(f"⚠️ User '{username}' already exists")
                await conn.close()
                return True

            # Create user
            await conn.execute(f"CREATE USER {username} WITH PASSWORD $1", password)

            # Grant permissions
            if databases:
                for db in databases:
                    await conn.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db} TO {username}")

            print(f"✅ Created user '{username}'")
            await conn.close()
            return True

        except Exception as e:
            print(f"❌ Failed to create user '{username}': {e}")
            return False

    async def setup_database_schema(self, db_name: str, schema_file: Path) -> bool:
        """Setup database schema from SQL file"""
        try:
            if not schema_file.exists():
                print(f"❌ Schema file not found: {schema_file}")
                return False

            # Read schema file
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            # Connect to target database
            conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                user=self.admin_user,
                password=self.admin_password,
                database=db_name
            )

            # Execute schema
            await conn.execute(schema_sql)
            print(f"✅ Executed schema from {schema_file}")

            await conn.close()
            return True

        except Exception as e:
            print(f"❌ Failed to setup schema: {e}")
            return False

    async def run_migrations(self, db_name: str, migrations_dir: Path) -> bool:
        """Run database migrations"""
        try:
            if not migrations_dir.exists():
                print(f"❌ Migrations directory not found: {migrations_dir}")
                return False

            # Connect to database
            conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                user=self.admin_user,
                password=self.admin_password,
                database=db_name
            )

            # Create migrations table if not exists
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Get applied migrations
            applied = await conn.fetchval("""
                SELECT array_agg(version) FROM schema_migrations
            """) or []

            # Find new migrations
            migration_files = sorted(migrations_dir.glob("*.sql"))
            new_migrations = []

            for mig_file in migration_files:
                version = mig_file.stem
                if version not in applied:
                    new_migrations.append((version, mig_file))

            if not new_migrations:
                print("✅ No new migrations to apply")
                await conn.close()
                return True

            # Apply migrations
            for version, mig_file in new_migrations:
                print(f"Applying migration: {version}")

                with open(mig_file, "r", encoding="utf-8") as f:
                    migration_sql = f.read()

                await conn.execute(migration_sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES ($1)",
                    version
                )

            print(f"✅ Applied {len(new_migrations)} migrations")
            await conn.close()
            return True

        except Exception as e:
            print(f"❌ Failed to run migrations: {e}")
            return False

    async def backup_database(self, db_name: str, backup_file: Path) -> bool:
        """Create database backup"""
        try:
            # Ensure backup directory exists
            backup_file.parent.mkdir(parents=True, exist_ok=True)

            # Use pg_dump for backup
            cmd = [
                "pg_dump",
                "-h", self.host,
                "-p", str(self.port),
                "-U", self.admin_user,
                "-F", "c",  # Custom format
                "-b",  # Include blobs
                "-v",  # Verbose
                "-f", str(backup_file),
                db_name
            ]

            # Set environment variable for password
            env = os.environ.copy()
            env["PGPASSWORD"] = self.admin_password

            result = subprocess.run(
                cmd,
                env=env,
                check=True,
                capture_output=True,
                text=True
            )

            print(f"✅ Database backup created: {backup_file}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Backup failed: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Backup error: {e}")
            return False

    async def restore_database(self, backup_file: Path, db_name: str) -> bool:
        """Restore database from backup"""
        try:
            if not backup_file.exists():
                print(f"❌ Backup file not found: {backup_file}")
                return False

            # Use pg_restore for restore
            cmd = [
                "pg_restore",
                "-h", self.host,
                "-p", str(self.port),
                "-U", self.admin_user,
                "-d", db_name,
                "-v",  # Verbose
                "-c",  # Clean (drop existing objects)
                str(backup_file)
            ]

            # Set environment variable for password
            env = os.environ.copy()
            env["PGPASSWORD"] = self.admin_password

            result = subprocess.run(
                cmd,
                env=env,
                check=True,
                capture_output=True,
                text=True
            )

            print(f"✅ Database restored from: {backup_file}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Restore failed: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Restore error: {e}")
            return False


class DatabaseSetupAutomation:
    """Main database setup automation class"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.scripts_dir = self.project_root / "scripts"
        self.sql_dir = self.project_root / "sql"

        # Environment configurations
        self.env_configs = {
            "development": {
                "database": "filemanager_dev",
                "username": "filemanager_dev",
                "password": "dev_password",
                "description": "Development database"
            },
            "staging": {
                "database": "filemanager_staging",
                "username": "filemanager_staging",
                "password": "staging_password",
                "description": "Staging database"
            },
            "production": {
                "database": "filemanager_prod",
                "username": "filemanager_prod",
                "password": "prod_password",
                "description": "Production database"
            }
        }

    def generate_secure_password(self, length: int = 16) -> str:
        """Generate secure password"""
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def create_database_schema(self) -> Path:
        """Create database schema SQL file"""
        schema_sql = """-- FileManager Telegram Bot Database Schema
-- Generated on: {datetime}

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Devices table
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    device_token VARCHAR(255) UNIQUE NOT NULL,
    device_name VARCHAR(255),
    device_info JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- File operations log
CREATE TABLE IF NOT EXISTS file_operations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    operation_type VARCHAR(50) NOT NULL, -- upload, download, delete, list
    file_path TEXT NOT NULL,
    file_size BIGINT,
    operation_status VARCHAR(50) DEFAULT 'pending', -- pending, completed, failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(255) NOT NULL,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Compliance and legal tables
CREATE TABLE IF NOT EXISTS user_agreements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agreement_version VARCHAR(50) NOT NULL,
    agreed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET
);

CREATE TABLE IF NOT EXISTS compliance_audits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audit_type VARCHAR(100) NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_devices_user_id ON devices(user_id);
CREATE INDEX IF NOT EXISTS idx_devices_token ON devices(device_token);
CREATE INDEX IF NOT EXISTS idx_file_operations_user_id ON file_operations(user_id);
CREATE INDEX IF NOT EXISTS idx_file_operations_created_at ON file_operations(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (will be overridden by config)
-- This is just a placeholder - actual admin setup should be done via environment variables
-- INSERT INTO users (telegram_id, username, is_admin) VALUES (0, 'admin', true);

COMMIT;
"""

        schema_file = self.sql_dir / "schema.sql"
        schema_file.parent.mkdir(exist_ok=True)

        with open(schema_file, "w", encoding="utf-8") as f:
            f.write(schema_sql)

        print(f"✅ Created database schema: {schema_file}")
        return schema_file

    def create_migrations_directory(self) -> Path:
        """Create migrations directory with initial migration"""
        migrations_dir = self.sql_dir / "migrations"
        migrations_dir.mkdir(exist_ok=True)

        # Create initial migration
        migration_sql = """-- Migration: 001_initial_schema
-- Description: Initial database schema

-- This migration contains the complete initial schema
-- It will be applied only if no migrations have been run before

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Devices table
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    device_token VARCHAR(255) UNIQUE NOT NULL,
    device_name VARCHAR(255),
    device_info JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- File operations log
CREATE TABLE IF NOT EXISTS file_operations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    operation_type VARCHAR(50) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    operation_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(255) NOT NULL,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User agreements table
CREATE TABLE IF NOT EXISTS user_agreements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agreement_version VARCHAR(50) NOT NULL,
    agreed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET
);

-- Compliance audits table
CREATE TABLE IF NOT EXISTS compliance_audits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audit_type VARCHAR(100) NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_devices_user_id ON devices(user_id);
CREATE INDEX IF NOT EXISTS idx_devices_token ON devices(device_token);
CREATE INDEX IF NOT EXISTS idx_file_operations_user_id ON file_operations(user_id);
CREATE INDEX IF NOT EXISTS idx_file_operations_created_at ON file_operations(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""

        migration_file = migrations_dir / "001_initial_schema.sql"
        with open(migration_file, "w", encoding="utf-8") as f:
            f.write(migration_sql)

        print(f"✅ Created initial migration: {migration_file}")
        return migrations_dir

    async def setup_environment_database(self, environment: str) -> bool:
        """Setup database for specific environment"""
        print(f"🗄️ Setting up {environment} database...")
        print("=" * 50)

        # Get environment configuration
        env_config = self.env_configs.get(environment)
        if not env_config:
            print(f"❌ Unknown environment: {environment}")
            return False

        # Initialize database manager
        db_manager = DatabaseManager()

        # Test connection
        if not await db_manager.test_connection():
            print("❌ Cannot connect to PostgreSQL server")
            print("Please ensure PostgreSQL is running and accessible")
            return False

        # Create database
        db_name = env_config["database"]
        username = env_config["username"]
        password = env_config["password"]

        print(f"📋 Database: {db_name}")
        print(f"👤 User: {username}")
        print(f"🔑 Password: {password[:8]}...")

        if not await db_manager.create_database(db_name, username):
            return False

        # Create user
        if not await db_manager.create_user(username, password, [db_name]):
            return False

        # Create schema
        schema_file = self.create_database_schema()
        if not await db_manager.setup_database_schema(db_name, schema_file):
            return False

        # Create migrations directory
        migrations_dir = self.create_migrations_directory()

        # Run migrations
        if not await db_manager.run_migrations(db_name, migrations_dir):
            return False

        # Test connection to new database
        try:
            conn = await asyncpg.connect(
                host=db_manager.host,
                port=db_manager.port,
                user=username,
                password=password,
                database=db_name
            )

            # Get database info
            result = await conn.fetchrow("""
                SELECT
                    current_database() as database,
                    current_user as username,
                    version() as version,
                    now() as current_time
            """)

            print("✅ Database setup completed successfully!")
            print(f"   Database: {result['database']}")
            print(f"   User: {result['username']}")
            print(f"   PostgreSQL: {result['version']}")
            print(f"   Connected at: {result['current_time']}")

            await conn.close()

        except Exception as e:
            print(f"❌ Database connection test failed: {e}")
            return False

        # Create backup
        backup_dir = self.project_root / "backups"
        backup_file = backup_dir / f"{db_name}_initial_{int(time.time())}.backup"

        print("💾 Creating initial backup...")
        if await db_manager.backup_database(db_name, backup_file):
            print(f"✅ Initial backup created: {backup_file}")

        return True

    def run_interactive_setup(self):
        """Run interactive database setup"""
        print("🗄️ PostgreSQL Database Setup Automation")
        print("=" * 60)
        print()
        print("This script will help you set up PostgreSQL databases for your bot.")
        print()

        # Environment selection
        print("Select environment to setup:")
        print("1. Development (local development)")
        print("2. Staging (testing environment)")
        print("3. Production (live environment)")

        while True:
            choice = input("Enter choice (1-3): ").strip()
            if choice == "1":
                environment = "development"
                break
            elif choice == "2":
                environment = "staging"
                break
            elif choice == "3":
                environment = "production"
                break
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")

        # Run setup
        async def run_setup():
            success = await self.setup_environment_database(environment)

            if success:
                print("\n🎉 Database setup completed!")
                print(f"Your {environment} database is ready to use.")
            else:
                print("\n❌ Database setup failed.")
                print("Please check the errors above and try again.")

        asyncio.run(run_setup())

    def run_command_line_setup(self, args):
        """Run command line database setup"""
        environment = args.environment

        async def run_setup():
            success = await self.setup_environment_database(environment)

            if not success:
                sys.exit(1)

        asyncio.run(run_setup())


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PostgreSQL Database Setup Automation")
    parser.add_argument(
        "--environment", "-e",
        choices=["development", "staging", "production"],
        help="Environment to setup"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run interactive setup"
    )
    parser.add_argument(
        "--create-user",
        action="store_true",
        help="Create database user only"
    )
    parser.add_argument(
        "--database-name",
        help="Database name to create"
    )
    parser.add_argument(
        "--username",
        help="Database username"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="PostgreSQL host"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5432,
        help="PostgreSQL port"
    )

    args = parser.parse_args()

    setup = DatabaseSetupAutomation()

    if args.interactive or not args.environment:
        setup.run_interactive_setup()
    else:
        setup.run_command_line_setup(args)


if __name__ == "__main__":
    main()