from django.conf import settings
from django.test import override_settings

import pytest


@override_settings(INSTALLED_APPS=settings.INSTALLED_APPS + ["axes"])
def test_module_import():
    try:
        import maykin_django_utils.mixins  # noqa: F401
    except ImportError:
        pytest.fail("Module 'mixins' is not imported correctly.")
