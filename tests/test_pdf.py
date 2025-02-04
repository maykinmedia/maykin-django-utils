import pytest


def test_module_import():
    try:
        import maykin_django_utils.pdf  # noqa: F401
    except ImportError:
        pytest.fail("Module 'pdf' is not imported correctly.")
