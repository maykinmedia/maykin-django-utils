"""
Structured logging helpers for Celery.
"""

import logging
import logging.config

from django.conf import settings

from celery.signals import setup_logging

from .config import structlog_configure_defaults


def setup_celery_structlog(format_exc_info: bool = True):
    """
    Apply the ``settings.LOGGING`` config to Celery and initialize structlog.
    """

    def _receiver_setup_logging(
        loglevel, logfile, format, colorize, **kwargs
    ):  # pragma: no cover
        # applies the settings.LOGGING configuration to Celery as well
        logging.config.dictConfig(settings.LOGGING)
        structlog_configure_defaults(format_exc_info=format_exc_info)

    setup_logging.connect(_receiver_setup_logging)

    return _receiver_setup_logging
