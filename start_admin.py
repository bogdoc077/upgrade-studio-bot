#!/usr/bin/env python3
"""
Upgrade Studio Bot Admin Panel Startup Script
"""
import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from admin.app import app
from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('admin_panel.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Start the admin panel server"""
    try:
        logger.info("Starting Upgrade Studio Bot Admin Panel...")
        logger.info(f"Admin panel will be available at: http://localhost:{settings.admin_port}")
        logger.info(f"Login with username: {settings.admin_username}")
        
        import uvicorn
        uvicorn.run(
            "admin.app:app",
            host=settings.admin_host,
            port=settings.admin_port,
            log_level=settings.log_level.lower(),
            reload=False  # Set to True for development
        )
    except KeyboardInterrupt:
        logger.info("Admin panel stopped by user")
    except Exception as e:
        logger.error(f"Failed to start admin panel: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()