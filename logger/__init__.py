from .logger import CustomLogger

# Create a global logger instance
logger = CustomLogger(
    logger_name="ChatMed",
).get_logger()

__all__ = ["logger"]
