import importlib.util

import pytest


def _dependency_installed(dependency: str):
    module = importlib.util.find_spec(dependency)
    return module is not None


@pytest.mark.skipif(
    _dependency_installed("weasyprint"), reason="The 'pdf' extra seems to be installed"
)
def test_pdf():
    with pytest.raises(ImportError):
        import maykin_common.pdf  # noqa: F401


@pytest.mark.skipif(
    _dependency_installed("maykin_2fa"), reason="The 'mfa' extra seems to be installed"
)
def test_2fa():
    with pytest.raises(ImportError):
        import maykin_common.django_two_factor_auth  # noqa: F401


@pytest.mark.skipif(
    _dependency_installed("axes"), reason="The 'axes' extra seems to be installed"
)
def test_mixins():
    with pytest.raises(ImportError):
        import maykin_common.throttling  # noqa: F401


@pytest.mark.skipif(
    _dependency_installed("opentelemetry"),
    reason="The 'otel' extra seems to be installed",
)
def test_otel():
    with pytest.raises(ImportError):
        import maykin_common.otel  # noqa: F401


def test_wsgi_middleware_always_works():
    from maykin_common.logging.wsgi import LogVars

    def dummy_app(environ, respond):
        respond("200 OK", [("Content-Type", "text/plain")])
        return [b"dummy!"]

    def start_response(status, headers, exc_info=None):
        pass

    application = LogVars(dummy_app)

    response = application({}, start_response)

    assert b"".join(response) == b"dummy!"


@pytest.mark.skipif(
    _dependency_installed("structlog") or _dependency_installed("celery"),
    reason="The 'structlog' extra or 'celery' seem to be installed",
)
def test_other_logging_modules_raise_importerror():
    with pytest.raises(ImportError):
        import maykin_common.logging.celery
    with pytest.raises(ImportError):
        import maykin_common.logging.config
    with pytest.raises(ImportError):
        import maykin_common.logging.processors  # noqa: F401
