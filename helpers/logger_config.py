import logging
import os

# Fetch the log level from the environment variable, default to DEBUG if not set
log_level = os.getenv('LOG_LEVEL', 'DEBUG').upper()

# Configure logging
logging.basicConfig(level=getattr(logging, log_level, logging.DEBUG), format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.debug("Logger configured with log level: %s %s", log_level, getattr(logging, log_level, logging.DEBUG))