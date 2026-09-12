import importlib.util

import pytest
import structlog

from maykin_common.logging.celery import setup_celery_structlog
from maykin_common.logging.config import structlog_configure_defaults


@pytest.fixture(autouse=True)
def reset_structlog():
    structlog.reset_defaults()


def test_can_configure_structlog_defaults():
    structlog_configure_defaults()

    assert structlog.is_configured


@pytest.mark.skipif(
    importlib.util.find_spec("celery") is None, reason="Celery not installed"
)
def test_connect_celery_logging_receiver():
    """
    Smoke test for celery logging setup.
    """
    from celery.signals import setup_logging

    assert not setup_logging.has_listeners()

    _receiver = setup_celery_structlog()

    assert setup_logging.has_listeners()
    # cleanup
    setup_logging.disconnect(_receiver)
