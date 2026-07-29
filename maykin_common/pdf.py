"""
Utilities for PDF rendering from HTML using WeasyPrint.

Note that you need to add https://pypi.org/project/weasyprint/ to your dependencies
if you want to make use of HTML-to-PDF rendering. This is not included by default as
it's quite heavy and requires OS-level dependencies.

This module exposes the public function :func:`render_to_pdf` which renders a template
with a context into a PDF document (bytes output). You can use "external" stylesheets
in these templates, and they will be resolved through django's staticfiles machinery
by the custom :class:`UrlFetcher`.

Depends on ``weasyprint``.
"""

import functools
import logging
import mimetypes
from collections.abc import Collection, Mapping
from io import BytesIO
from pathlib import PurePosixPath
from typing import NotRequired, TypedDict
from urllib.parse import ParseResult, urlparse

from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.signals import setting_changed
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.module_loading import import_string

import weasyprint

from maykin_common.settings import get_setting

logger = logging.getLogger(__name__)

__all__ = ["render_template_to_pdf", "render_to_pdf"]


DEFAULT_ALLOWED_PROTOCOLS: Collection[str] = (
    "http",
    "https",
    "data",
)
"""
A lowercase collection of URL protocols that Weasyprint may resolve.

This is a security feature. Protocols like ``file://`` could be used to extract host
level files into the PDF data through malicious URLs.
"""


def get_base_url() -> str:
    """
    Get the base URL where the project is served.
    """

    if pdf_base_url_function := get_setting("PDF_BASE_URL_FUNCTION"):
        return import_string(pdf_base_url_function)()
    raise NotImplementedError("You must implement 'get_base_url'.")


def _ensure_fully_qualified_url(url: str, base: ParseResult) -> ParseResult:
    """
    Ensure the passed in URL is fully qualified.

    If the URL does not have a network location, we take the protocol and netloc from
    the provided base URL to make it fully qualified. This assumes no netloc implies
    no protocol.
    """
    parsed_url = urlparse(url)
    match parsed_url:
        case ParseResult(scheme=scheme, netloc=netloc) if scheme and netloc:
            return parsed_url
        case _:
            # it is documented as public API!
            return parsed_url._replace(scheme=base.scheme, netloc=base.netloc)


@functools.cache
def _get_candidate_storages() -> Mapping[ParseResult, FileSystemStorage]:
    """
    Introspect settings and determine which storages can serve static assets.

    We can only consider storages that inherit from :class:`FileSystemStorage` for
    optimized asset serving. The goal of this module is to avoid network round-trips to
    our own ``MEDIA_ROOT`` or ``STATIC_ROOT``.
    """
    base_url = urlparse(get_base_url())
    candidates: dict[ParseResult, FileSystemStorage] = {}

    # check staticfiles app
    if isinstance(staticfiles_storage, FileSystemStorage):
        static_url = _ensure_fully_qualified_url(settings.STATIC_URL, base=base_url)
        candidates[static_url] = staticfiles_storage

    # check media root
    if isinstance(default_storage, FileSystemStorage):
        media_url = _ensure_fully_qualified_url(settings.MEDIA_URL, base=base_url)
        candidates[media_url] = default_storage

    return candidates


@receiver(setting_changed, dispatch_uid="maykin_common.pdf._reset_storages")
def _reset_storages(sender, setting: str, **kwargs):
    # mostly for tests, settings *should* not change in production code
    match setting:
        case "STATIC_ROOT" | "MEDIA_ROOT" | "STORAGES" | "PDF_BASE_URL_FUNCTION":
            _get_candidate_storages.cache_clear()
        case _:  # pragma: no cover
            pass


class UrlFetcherResult(TypedDict):
    mime_type: str | None
    encoding: str | None
    redirected_url: str
    filename: str
    file_obj: NotRequired[BytesIO]
    string: NotRequired[bytes]


class UrlFetcher:
    """
    URL fetcher that skips the network for /static/* and /media/* files.
    """

    def __init__(
        self,
        allowed_protocols: Collection[str] | None,
        _fail_on_errors: bool = False,
    ):
        self.allowed_protocols = allowed_protocols
        self._fail_on_errors = _fail_on_errors

    def __call__(self, url: str) -> UrlFetcherResult:
        """
        Check if the URL matches one of our candidates and use it if there's a match.

        Matching is done on the URLs of the storages and the requested asset. If the
        prefix matches, look up the relative asset path in the storage and serve it
        if it's found. If not, defer to the default URL fetcher of WeasyPrint.
        """
        # We don't need to parse the url if data is included directly,
        # e.g. base64-encoded images.
        if url.startswith("data:"):
            # TODO: deprecated since weasyprint 68, replace with URLFetcher
            return weasyprint.default_url_fetcher(
                url, allowed_protocols=self.allowed_protocols
            )  # pyright:ignore[reportReturnType]

        parsed_url = urlparse(url)

        # Try candidates, respecting the order of the candidate configuration.
        for base, storage in _get_candidate_storages().items():
            base_url = base.geturl()
            # Skip to the next candidate if the URLs don't share a prefix.
            if not url.startswith(base_url):
                continue

            # get the relative path to lookup in the storage to obtain an absolute path
            rel_path = PurePosixPath(parsed_url.path).relative_to(base.path)
            rel_path_str = str(rel_path)

            absolute_path: str | None = None
            if storage.exists(rel_path_str):
                absolute_path = storage.path(rel_path_str)
            elif settings.DEBUG and storage is staticfiles_storage:
                # use finders so that it works in dev too, we already check that it's
                # using filesystem storage earlier
                absolute_path = finders.find(rel_path_str)

            # we bail out, since we hit a storage that matches the URL prefix. Other
            # candidates will not have match either due to their different URL prefixes.
            if absolute_path is None:
                logger.error(
                    "path_resolution_failed",
                    extra={
                        "path": rel_path_str,
                        "storage": storage,
                    },
                )
                # TODO: deprecated since weasyprint 68, replace with URLFetcher
                return weasyprint.default_url_fetcher(
                    url, allowed_protocols=self.allowed_protocols
                )  # pyright:ignore[reportReturnType]

            content_type, encoding = mimetypes.guess_type(absolute_path)
            result: UrlFetcherResult = {
                "mime_type": content_type,
                "encoding": encoding,
                "redirected_url": url,
                "filename": rel_path.parts[-1],
            }
            with open(absolute_path, "rb") as f:
                result["file_obj"] = BytesIO(f.read())
            return result

        # all candidates were tried, none were a match -> defer to the weasyprint
        # default
        return weasyprint.default_url_fetcher(
            url, allowed_protocols=self.allowed_protocols
        )  # pyright:ignore[reportReturnType]


def render_to_pdf(
    html: str,
    variant: str | None = "pdf/ua-1",
    allowed_protocols: Collection[str] | None = DEFAULT_ALLOWED_PROTOCOLS,
    _urlfetcher_fail_on_errors: bool = False,
) -> tuple[str, bytes]:
    """
    Render the provided HTML to PDF.

    The default ``variant`` generates accessible PDFs. Technically it's still an
    experimental feature in WeasyPrint, so if it's causing issues, you can pass
    ``variant=None`` instead.
    """
    html_object = weasyprint.HTML(
        string=html,
        url_fetcher=UrlFetcher(
            allowed_protocols=allowed_protocols,
            _fail_on_errors=_urlfetcher_fail_on_errors,
        ),
        base_url=get_base_url(),
    )
    pdf = html_object.write_pdf(pdf_variant=variant)
    assert isinstance(pdf, bytes)
    return html, pdf


def render_template_to_pdf(
    template_name: str,
    context: dict[str, object],
    variant: str | None = "pdf/ua-1",
    allowed_protocols: Collection[str] | None = DEFAULT_ALLOWED_PROTOCOLS,
    _urlfetcher_fail_on_errors: bool = False,
) -> tuple[str, bytes]:
    """
    Render a (HTML) template to PDF with the given context.
    """
    rendered_html = render_to_string(template_name, context=context)
    return render_to_pdf(
        rendered_html,
        variant=variant,
        allowed_protocols=allowed_protocols,
        _urlfetcher_fail_on_errors=_urlfetcher_fail_on_errors,
    )
