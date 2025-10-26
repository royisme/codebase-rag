#!/usr/bin/env python3
"""
Database initialization script.
Run this script to create all database tables and initialize default data.
"""

import asyncio
import sys

from database.init_db import init_database
from security.initialization import ensure_default_superuser, ensure_default_policies
from database.session import async_session_factory
from loguru import logger


async def main():
    """Initialize database and create default superuser."""
    try:
        logger.info("Starting database initialization...")

        # Create database tables
        await init_database()
        logger.info("Database tables created")

        # Create default superuser
        async with async_session_factory():
            superuser = await ensure_default_superuser()
            if superuser:
                logger.info(f"Default superuser created: {superuser.email}")
            else:
                logger.info("Default superuser already exists")

        # Initialize default policies
        await ensure_default_policies(superuser_id=superuser.id if superuser else None)
        logger.info("Default policies initialized")

        logger.info("Database initialization completed successfully!")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
