import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.captureWarnings(True)

    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(level)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # stdout
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)

    log_file = os.getenv("LOG_FILE_PATH")
    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=2)
        fh.setFormatter(fmt)
        root.addHandler(fh)
