import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
import colorlog


class CustomLogger:
    def __init__(
        self,
        logger_name: str = "Chatbot",
        log_level: int = logging.INFO,
        log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    ):
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Create logger
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(log_level)

        # Prevent adding handlers multiple times
        if not self.logger.handlers:
            # Console Handler with colors
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)

            # Color scheme for different log levels
            color_scheme = {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            }

            # Create color formatter
            color_formatter = colorlog.ColoredFormatter(
                f"%(log_color)s{log_format}%(reset)s",
                log_colors=color_scheme,
                reset=True,
                style="%",
            )
            console_handler.setFormatter(color_formatter)

            # File Handler
            today = datetime.now().strftime("%Y-%m-%d")
            file_handler = RotatingFileHandler(
                filename=f"logs/{logger_name}_{today}.log",
                maxBytes=10485760,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(log_level)

            # Create file formatter
            file_formatter = logging.Formatter(log_format)
            file_handler.setFormatter(file_formatter)

            # Add handlers to logger
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger
