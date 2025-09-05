import logging
import sys

# Custom log level for SUCCESS
SUCCESS_LEVEL_NUM = 25  # Between INFO (20) and WARNING (30)
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")


def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)


logging.Logger.success = success

# Colors (ANSI escape codes)
COLORS = {
    "INFO": "\033[1;34m",  # Blue
    "DEBUG": "\033[37m",  # White
    "SUCCESS": "\033[1;32m",  # Bold Green
    "WARNING": "\033[1;93m",  # Bright Yellow
    "ERROR": "\033[1;31m",  # Red
    "CRITICAL": "\033[1;31m",  # Bold Red
}
RESET = "\033[0m"


class ColorFormatter(logging.Formatter):
    def format(self, record):
        color = COLORS.get(record.levelname, "")
        message = super().format(record)
        return f"{color}{message}{RESET}"


def init_logging(level=logging.DEBUG, log_file=None):
    """Initialize logging with color and optional file output."""
    logger = logging.getLogger()
    logger.setLevel(level)
    logger.handlers.clear()

    # Console handler with colors + time
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        ColorFormatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
    )
    logger.addHandler(console_handler)

    # File handler (no colors, with date)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        logger.addHandler(file_handler)

    return logger


# Example usage:
if __name__ == "__main__":
    log = init_logging(log_file="app.log")

    log.debug("This is a debug message")
    log.info("This is an info message")
    log.success("Operation completed successfully!")
    log.warning("This is a warning")
    log.error("This is an error")
    log.critical("This is critical")
