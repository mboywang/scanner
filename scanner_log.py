"""
Central logging for the Scanner app.

Two destinations:
  * Detailed rolling log (everything, for debugging) at
    %LOCALAPPDATA%\\ScannerApp\\logs\\scanner.log
  * Human-readable activity log (key events only, for the team to review) at
    <output folder>\\_scanner_activity.log

Use logger.debug/info/error(...) for detailed-only messages, and
activity(logger, "...") for events that should also appear in the shared,
human-readable log.
"""
import os
import tempfile
import logging
from logging.handlers import RotatingFileHandler

SHARED_FOLDER = r"C:\Users\mboyw\MSPbots.ai\Back Office Team - Home scanner"

_configured = False


class _ActivityFilter(logging.Filter):
    """Only let records explicitly marked as activity into the shared log."""
    def filter(self, record):
        return getattr(record, 'activity', False)


def get_logger():
    """Return the shared 'scanner' logger, configuring handlers once."""
    global _configured
    logger = logging.getLogger('scanner')
    if _configured:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # 1) Detailed rolling log on the local machine (always available).
    try:
        base = os.environ.get('LOCALAPPDATA') or tempfile.gettempdir()
        log_dir = os.path.join(base, 'ScannerApp', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        fh = RotatingFileHandler(
            os.path.join(log_dir, 'scanner.log'),
            maxBytes=1_000_000, backupCount=5, encoding='utf-8'
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s  %(levelname)-7s  %(message)s', '%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(fh)
    except Exception:
        pass

    # 2) Human-readable activity log in the shared team folder (best effort;
    #    the folder may be offline / syncing).
    try:
        os.makedirs(SHARED_FOLDER, exist_ok=True)
        sh = RotatingFileHandler(
            os.path.join(SHARED_FOLDER, '_scanner_activity.log'),
            maxBytes=500_000, backupCount=3, encoding='utf-8'
        )
        sh.setLevel(logging.INFO)
        sh.addFilter(_ActivityFilter())
        sh.setFormatter(logging.Formatter('%(asctime)s  %(message)s', '%Y-%m-%d %H:%M:%S'))
        logger.addHandler(sh)
    except Exception:
        pass

    _configured = True
    return logger


def activity(logger, message):
    """Log a human-facing event to BOTH the detailed and shared logs."""
    logger.info(message, extra={'activity': True})
