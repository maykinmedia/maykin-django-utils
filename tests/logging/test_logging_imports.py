import pytest


def test_module_import_config():
    try:
        import maykin_common.logging.config  # noqa: F401
    except ImportError:
        pytest.fail("Module 'logging.config' is not imported correctly.")


def test_module_import_celery():
    try:
        import maykin_common.logging.celery  # noqa: F401
    except ImportError:
        pytest.fail("Module 'logging.config' is not imported correctly.")


def test_module_import_processors():
    try:
        import maykin_common.logging.processors  # noqa: F401
    except ImportError:
        pytest.fail("Module 'logging.config' is not imported correctly.")
