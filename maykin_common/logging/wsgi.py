"""
Helpers related to structured (JSON) logging for the uwsgi application server.
"""

from datetime import UTC, datetime

try:
    import uwsgi  # pyright: ignore[reportMissingModuleSource] uwsgi magic...
except ImportError:
    uwsgi = None


class LogVars:
    """
    A WSGI-middleware to inject log variables for uwsgi.

    It makes the following log variables available to uwsgi:

    * ``iso8601timestamp``: ISO-8601 formatted 'now' timestamp.

    Usage::
        from django.core.wsgi import get_wsgi_application

        application = LogVars(get_wsgi_application())
    """

    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        if uwsgi is not None:  # pragma: no cover - can't test this outside of uwsgi...
            now = datetime.now(tz=UTC)
            uwsgi.set_logvar("iso8601timestamp", now.isoformat())
        return self.application(environ, start_response)
