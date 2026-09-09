from unittest.mock import patch

from django.core.management import call_command

import pytest
from weasyprint.urls import FatalURLFetchingError, URLFetcherResponse

from maykin_common.pdf import render_template_to_pdf


def get_base_url():
    return "http://testserver"


@pytest.fixture(autouse=True)
def _collectstatic(settings, tmp_path):
    static_root = tmp_path / "static_root"
    settings.STATIC_ROOT = str(static_root)
    call_command("collectstatic", interactive=False, link=True, verbosity=0)
    yield


@pytest.fixture(autouse=True)
def _settings(settings):
    settings.PDF_BASE_URL_FUNCTION = f"{__name__}.get_base_url"


@pytest.fixture()
def dummy_urlfetch_result():
    # WeasyPrint closes the response's underlying file object once it's done
    # consuming it, so we need a factory + side effect for mocking
    def _make_response(*args, **kwargs):
        return URLFetcherResponse(
            "dummy://",
            body=b"",
            headers={"Content-Type": "text/css"},
        )

    return _make_response


def test_raises_if_setting_not_configured_properly(settings):
    settings.PDF_BASE_URL_FUNCTION = None

    with pytest.raises(NotImplementedError):
        render_template_to_pdf(
            "testapp/pdf/hello_world.html",
            {},
            _urlfetcher_fail_on_errors=True,
        )


def test_render_template_returns_html():
    html, pdf = render_template_to_pdf(
        "testapp/pdf/hello_world.html",
        {"world": "pytest"},
        _urlfetcher_fail_on_errors=True,
    )

    assert isinstance(html, str)
    assert "Hello pytest" in html
    assert isinstance(pdf, bytes)


def test_external_url_uses_default_resolver(dummy_urlfetch_result):
    with patch(
        "maykin_common.pdf.weasyprint.URLFetcher.fetch",
        side_effect=dummy_urlfetch_result,
    ) as mock_fetcher:
        render_template_to_pdf(
            "testapp/pdf/external_url.html",
            {},
            _urlfetcher_fail_on_errors=True,
        )

    mock_fetcher.assert_called_once_with("https://example.com/index.css", headers=None)


def test_local_asset_does_not_use_default_resolver(dummy_urlfetch_result):
    with patch(
        "maykin_common.pdf.weasyprint.URLFetcher.fetch",
        side_effect=dummy_urlfetch_result,
    ) as mock_fetcher:
        render_template_to_pdf(
            "testapp/pdf/local_url.html",
            {},
            _urlfetcher_fail_on_errors=True,
        )

    mock_fetcher.assert_not_called()


def test_render_with_missing_asset(dummy_urlfetch_result):
    with patch(
        "maykin_common.pdf.weasyprint.URLFetcher.fetch",
        side_effect=dummy_urlfetch_result,
    ) as mock_fetcher:
        render_template_to_pdf(
            "testapp/pdf/missing_asset.html",
            {},
            _urlfetcher_fail_on_errors=True,
        )

    mock_fetcher.assert_called_once_with(
        "http://testserver/static/non_existent.css",
        headers=None,
    )


def test_resolves_assets_in_debug_mode(settings, dummy_urlfetch_result):
    settings.STATIC_ROOT = "/bad/path"
    settings.DEBUG = True

    with patch(
        "maykin_common.pdf.weasyprint.URLFetcher.fetch",
        side_effect=dummy_urlfetch_result,
    ) as mock_fetcher:
        render_template_to_pdf(
            "testapp/pdf/local_url.html",
            {},
            _urlfetcher_fail_on_errors=True,
        )

    mock_fetcher.assert_not_called()


def test_fully_qualified_static_url(settings, dummy_urlfetch_result):
    settings.STATIC_URL = "http://testserver/static/"

    with patch(
        "maykin_common.pdf.weasyprint.URLFetcher.fetch",
        side_effect=dummy_urlfetch_result,
    ) as mock_fetcher:
        render_template_to_pdf(
            "testapp/pdf/local_url.html",
            {},
            _urlfetcher_fail_on_errors=True,
        )

    mock_fetcher.assert_not_called()


def test_other_storages_than_file_system_storage(settings, dummy_urlfetch_result):
    settings.STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            # this causes the /static/ prefix to be absent (!)
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
    }

    with patch(
        "maykin_common.pdf.weasyprint.URLFetcher.fetch",
        side_effect=dummy_urlfetch_result,
    ) as mock_fetcher:
        render_template_to_pdf(
            "testapp/pdf/local_url.html",
            {},
            _urlfetcher_fail_on_errors=True,
        )

    mock_fetcher.assert_called_with(
        "http://testserver/testapp/some.css",
        headers=None,
    )


def test_base64_encoded_image(dummy_urlfetch_result):
    with patch(
        "maykin_common.pdf.weasyprint.URLFetcher.fetch",
        side_effect=dummy_urlfetch_result,
    ) as mock_fetcher:
        render_template_to_pdf(
            "testapp/pdf/base64_encoded_image.html",
            {},
            _urlfetcher_fail_on_errors=True,
        )

    mock_fetcher.assert_called_with(
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADkAAAA",
        headers=None,
    )


def test_blocks_suspicious_protocols_by_default():
    with pytest.raises(FatalURLFetchingError):
        render_template_to_pdf(
            "testapp/pdf/blocked_file_url.html",
            {},
            _urlfetcher_fail_on_errors=True,
        )
