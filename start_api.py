#!/usr/bin/env python3
"""
Upgrade Studio Bot API Server
"""
import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.server import app
from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api_server.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Start the API server"""
    try:
        logger.info("Starting Upgrade Studio Bot API Server...")
        logger.info(f"API server will be available at: http://localhost:8001")
        
        import uvicorn
        # Production mode - no reload
        uvicorn.run(
            "api.server:app",
            host="0.0.0.0",
            port=8001,
            log_level=settings.log_level.lower(),
            reload=False  # Production mode
        )
    except KeyboardInterrupt:
        logger.info("API server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()