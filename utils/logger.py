import logging
import sys


def setup_logger():
    logger = logging.getLogger(__name__)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                        stream=sys.stdout)

    return logger

