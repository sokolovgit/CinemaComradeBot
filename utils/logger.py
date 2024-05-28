import logging
import sys


def setup_logger():
    """
    Sets up a logger with basic configuration.

    The logger is set to log INFO level and higher messages. The format of the log message is:
    [Time of Log] - [Log Level] - [Logger Name] - [Log Message]

    The log messages are outputted to stdout.

    Returns:
        logging.Logger: The configured logger.
    """
    logger = logging.getLogger(__name__)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                        stream=sys.stdout)

    return logger

