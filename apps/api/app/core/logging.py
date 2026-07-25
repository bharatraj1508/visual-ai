import logging
import sys
from app.core.config import settings

# Define the log format
# %(asctime)s - Timestamp of the log
# %(levelname)-8s - Log level (e.g. INFO, ERROR), padded to 8 chars
# %(name)s - The logger name (usually module path)
# %(message)s - The actual log message
LOG_FORMAT = "%(asctime)s - %(levelname)-8s - %(name)s - %(message)s"


def setup_logging() -> None:
    # 1. Determine log level based on environment
    log_level = logging.DEBUG if settings.ENV == "development" else logging.INFO

    # 2. Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 3. Clean up existing default handlers (avoids double logging in FastAPI/Uvicorn)
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    # 4. Create standard output stream handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # 5. Set the format
    formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(formatter)

    # 6. Add handler to the root logger
    root_logger.addHandler(console_handler)

    # 7. Optionally configure log levels of other noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# Run configuration upon import
setup_logging()
logger = logging.getLogger("app")
