import sys
import os
from loguru import logger
from app.core.config import settings

def setup_logger():
    log_level = settings.log_level
    log_file = settings.log_file
    
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Configure Loguru
    config = {
        "handlers": [
            {
                "sink": sys.stdout,
                "format": "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                "level": log_level,
            },
            {
                "sink": log_file,
                "serialize": True,  # JSON format for production ingestion
                "rotation": "10 MB",
                "retention": "1 week",
                "level": log_level,
            }
        ]
    }
    
    logger.configure(**config)
    logger.info("Structured logging initialized.")
    return logger
