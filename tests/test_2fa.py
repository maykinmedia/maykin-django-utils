import pytest


def test_module_import():
    try:
        import maykin_django_utils.django_two_factor_auth  # noqa: F401
    except ImportError:
        pytest.fail("Module 'django_two_factor_auth' is not imported correctly.")
