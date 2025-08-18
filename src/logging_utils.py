import logging
import config

_DEF_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

_logging_configured = False

def setup_logging():
    global _logging_configured
    if _logging_configured:
        return
    logging.basicConfig(level=config.LOG_LEVEL, format=_DEF_FORMAT)
    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
