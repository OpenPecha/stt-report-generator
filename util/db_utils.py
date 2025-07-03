"""
Database utility functions for STT report generator.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import logging

logger = logging.getLogger("stt-report-generator")


def get_sqlalchemy_engine():
    """
    Creates an SQLAlchemy engine for database operations.
    
    Returns:
        engine: A SQLAlchemy engine object.
    """
    try:
        # Load environment variables from the util/.env file
        dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
        load_dotenv(dotenv_path=dotenv_path)
        
        # Get database URL (either from the full URL or construct it)
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            # Construct URL from components
            host = os.environ.get("HOST")
            dbname = os.environ.get("DBNAME")
            user = os.environ.get("DBUSER")
            password = os.environ.get("PASSWORD")
            db_url = f"postgresql://{user}:{password}@{host}/{dbname}"
        
        # Create engine
        engine = create_engine(db_url)
        logger.info("Successfully created SQLAlchemy engine")
        return engine
    except Exception as e:
        logger.error(f"Failed to create SQLAlchemy engine: {e}")
        raise
