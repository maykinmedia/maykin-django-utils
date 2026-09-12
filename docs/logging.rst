.. _logging:

==================
Structured logging
==================

.. versionadded:: 0.22.0

    Added tooling for structured logging.

Structured logging is the practice of emitting application logs in a format that's
easily parsed by machines and/or humans. Logging is one of the pilars of
:ref:`telemetry <otel>`.

Structured logs allow for easy context inclusion, such as correlation IDs with other
sources of telemetry (traces, spans, Sentry events...) and (global) request metadata.
If you're not familiar with structlog yet, you should `familiarize yourself <https://www.structlog.org/en/stable/getting-started.html>`_ with it.

Recommended setup
=================

maykin-common provides some buildings blocks to set up structured logs in your project.
The bulk of the work is done through the `structlog <https://www.structlog.org/>`_
library and the ``django-structlog`` binding.

To install the necessary dependencies, request the relevant extra:

.. code-block:: bash

    uv pip install maykin-common[structlog]

or, if you also use Celery:

.. code-block:: bash

    uv pip install maykin-common[structlog] django-structlog[celery]

Django settings
---------------

Import the necessary helpers in your settings:

.. code-block:: python

    from maykin_common.config import config
    from maykin_common.logging.config import (
        LOGGING_FORMATTERS,
        LOGGING_APPS,
        LOGGING_MIDDLEWARE,
        structlog_configure_defaults,
    )

**Installed apps**

Ensure the necessary apps are installed:

.. code-block:: python

    INSTALLED_APPS = [
        ...,
        *LOGGING_APPS,
        ...,
    ]

**Middleware**

If you wish to log requests/responses through middleware (recommended!), add the logging
middleware after the ``AuthenticationMiddleware`` so that the user can be extracted:

.. code-block:: python

    MIDDLEWARE = [
        ...,
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        *LOGGING_MIDDLEWARE,
        ...,
    ]

**Logging**

Arguable the most important Django setting :-) Note that we assume the setup from
``default-project`` which already has an initial custom ``LOGGING`` setup:

.. code-block:: python

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": LOGGING_FORMATTERS,
        "handlers": {
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": config("LOG_FORMAT_CONSOLE", default="json"),
            },
        },
        "loggers": ...,
    }

    # initialize/configure structlog
    structlog_configure_defaults()

By default some custom processors are included that:

* reduce noise in development.
* if OTel is enabled, correlated logs and traces.

**Django-structlog**

.. code-block:: python

    DJANGO_STRUCTLOG_IP_LOGGING_ENABLED = False

See the `library documentation <https://django-structlog.readthedocs.io/en/latest/configuration.html>`_ for additional settings.

**Sentry logging integration**

The default ``sentry_sdk`` setup sends application logs above a certain log level
(warning) to Sentry. Out of the box, this is not particularly compatible with structlog
due to various formatting issues and the amount of noise that can be produced.

We recommend disabling this integration entirely and using Loki/Grafana or similar
solutions for log scraping/ingestion and visualization.

In your projects ``conf/utils.py``, in the ``get_sentry_integrations`` function:

.. code-block:: python

    def get_sentry_integrations() -> list:
    """
    Determine which Sentry SDK integrations to enable.
    """
    default = [
        django.DjangoIntegration(),
        LoggingIntegration(
            level=logging.INFO,  # breadcrumbs
            # do not send any logs as event to Sentry at all - these must be scraped by
            # the (container) infrastructure instead.
            event_level=None,
        ),
        redis.RedisIntegration(),
    ]
    ...

Celery
------

If you use Celery, some additional setup is required as Celery has it's own logging
mechanism.

First, enable the Celery integration in settings:

.. code-block:: python

    DJANGO_STRUCTLOG_CELERY_ENABLED = True

Next, you'll want to properly wire up structlog for Celery (workers). In your
``celery.py`` module:

.. code-block:: python

    from celery import Celery
    from maykin_common.logging.celery import setup_celery_structlog

    app = Celery("app")
    app.config_from_object("django.conf:settings", namespace="CELERY")

    setup_celery_structlog()

    app.autodiscover_tasks()

uWSGI
-----

The maykin-common integration handles application-level logging, but application servers
like uWSGI also emit their own logs. To emit those in a structured format, some
additional configuration is necessary.

**WSGI middleware**

maykin-common provices a middleware to expose additional log variables to uWSGI. In your
project's ``wsgi.py``, enable it:

.. code-block:: python

    from django.core.wsgi import get_wsgi_application

    from maykin_common.logging.wsgi import LogVars

    application = LogVars(get_wsgi_application())

This is safe to apply even if you're not using uWSGI.

**uWSGI requirements**

Ensure that the following libraries are available where uwsgi is being built, otherwise
log-routing support is not available:

* ``libpcre3`` (runtime dependency)
* ``libpcre3-dev`` (build time dependency)

In the uwsgi invocation, ensure that the (to be created) config file is also loaded:

.. code-block:: bash

    # Figure out abspath of this script
    SCRIPT=$(readlink -f "$0")
    SCRIPTPATH=$(dirname "$SCRIPT")

    uwsgi \
        --strict \
        --ini "${SCRIPTPATH}/uwsgi.ini" \
        --other-options ... \

and configure logging in the config file:

.. code-block:: ini

    ; Docs:
    ; * https://uwsgi-docs.readthedocs.io/en/latest/Logging.html
    ; * https://uwsgi-docs.readthedocs.io/en/latest/LogEncoders.html
    ; Reference article: https://blog.rama.io/json-logging-with-uwsgi
    [uwsgi]
    ; logger definition for the django app logs, which are already structured
    logger = djangologger stdio
    ; logger definition for the uwsgi server logs
    logger = uwsgilogger stdio

    ; any message starting with { is assumed to already be structured ->
    ; send it to the djangologger
    log-route = djangologger ^{.*$
    ; send any message not starting with { to the uwsgilogger
    log-route = uwsgilogger ^((?!\{).)*$

    ; leave already JSON formatted django logs as is
    log-encoder = format:djangologger ${msg}
    ; Encode uWSGI server logs as JSON - deliberately using msg instead of event due to
    ; high cardinality of this key/label.
    log-encoder = json:uwsgilogger {"source": "uwsgi", "type": "server", "timestamp": "${strftime:%%Y-%%m-%%dT%%H:%%M:%%S%%z}", "msg": "${msg}", "level": "info"}

    ; these are uwsgi's own request logs (not to be confused with the request logs emitted
    ; by the application!)
    logger-req = stdio
    ; pragamatic approach - these variables are *not* JSON escaped and can lead to broken
    ; output lines. there's no security risk involved there, at worst a log scraper fails to
    ; parse the message as json
    ; TODO: perhaps we can extract trace IDs here for spans -> using uwsgi vars!
    log-format = {"source": "uwsgi", "event": "request", "method": "%(method)", "path": "%(uri)", "duration_in_ms": %(msecs), "status": %(status), "bytes": %(rsize), "referer": "%(referer)", "host": "%(host)", "timestamp": "%(iso8601timestamp)", "remote_ip": "%(addr)", "level": "info"}

    ; finally, ensure that all log lines are separated with a newline
    log-encoder = nl

gunicorn
--------

.. todo:: gunicorn is currently being explored.

Linter configuration
--------------------

To enforce that only ``structlog`` loggers are used, you can configure Ruff to ban
imports of the standard library in your ``pyproject.toml``:

.. code-block:: toml

    [tool.ruff.lint]
    extend-select = [
        "TID251",# tidy-imports banned API
    ]

    [tool.ruff.lint.flake8-tidy-imports.banned-api]
    "logging".msg = "Use `structlog.stdlib.get_logger(__name__)` instead of the stdlib logging module."


Usage and best practices
========================

Emitting logs
-------------

It helps to frame every logging action as *logging an event*. The log "message" in
structlog logs gets written as the `"event"` key to underline this principle. Each log
should describe something that happened, and provide the relevant context as keyword
arguments.

For example:

.. code-block:: python

    import structlog

    logger = structlog.stdlib.get_logger(__name__)

    def login_view(request):

        log_user_in(...)

        logger.info(
            "user_logged_in",
            username=request.user.username,
            is_staff=request.user.is_staff,
        )

        return ...

You should provide only the necessary context that may be relevant to reconstruct what
happened.

When including additional context, you'll usually want to limit this to primitives (
strings, numbers, ...) as structlog will call the ``repr(...)`` on non-JSON primitives.

Log context
-----------

You can and should set up relevant logging context for downstream calls. See the
`context variables <https://www.structlog.org/en/stable/contextvars.html>`_ documentation.

Suppressing django runserver logs
---------------------------------

If you enable the middleware to log requests and responses (recommended), then your
runserver output will become very noisy because Django also still emits request/response
logs.

You can suppress these in your ``LOGGING`` setting with a logger entry:

.. code-block:: python

    LOGGING = {
        ...,
        "loggers": {
            ...,
            # suppress django.server request logs because those are already emitted by
            # django-structlog middleware
            "django.server": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            ...,
        },
    }

Other library integrations
==========================

django-log-outgoing-requests
----------------------------

Django-log-outgoing-requests has a structlog processor
:class:`log_outgoing_requests.structlog.ExtractRequestAndResponseDetails` that you can
include in your processors pipeline.
