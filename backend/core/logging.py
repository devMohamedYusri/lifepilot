"""
Logging configuration for proper observability.
"""
import sys
import logging
from loguru import logger
from core.config import settings

def setup_logging():
    """Configure logging with Loguru."""
    # Remove default handler
    logger.remove()
    
    # Console handler (JSON in production, human-readable in dev)
    if settings.environment == "production":
        logger.add(
            sys.stderr,
            format="{time} {level} {message}",
            level="INFO",
            serialize=True
        )
    else:
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG"
        )
        
    # File handler (Rotation every day or 10MB)
    logger.add(
        "logs/lifepilot.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        compression="zip"
    )
    
    # Intercept standard library logging
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Silence noisy libraries
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
    
    return logger
