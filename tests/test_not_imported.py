import pytest


def test_pdf():
    with pytest.raises(ImportError):
        import maykin_django_utils.pdf  # noqa: F401


def test_2fa():
    with pytest.raises(ImportError):
        import maykin_django_utils.django_two_factor_auth  # noqa: F401


def test_mixins():
    with pytest.raises(ImportError):
        import maykin_django_utils.mixins  # noqa: F401
