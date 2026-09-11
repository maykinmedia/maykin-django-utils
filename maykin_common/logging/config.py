"""
Configuration constants for easy structured logging setup.

You can use this as a starting point if you just want a minimal, battle tested setup.
The configuration has been extracted from Open Forms, Open Inwoner and the GPP-Woo
projects.

When your specific project needs deviate from this configuration, it's recommended to
vendor it in your project and own the whole configuration. maykin-common will not
facilitate all kinds of configuration flags/parameters as that inevitably leads to
leaky abstracts and `Rube Goldberg machines <https://en.wikipedia.org/wiki/Rube_Goldberg_machine>`_
with unmaintainable complexity.
"""

import structlog

from .processors import add_open_telemetry_spans, drop_user_agent_in_dev

#
# INSTALLED_APPS
#
LOGGING_APPS = ["django_structlog"]

#
# MIDDLEWARE
#
LOGGING_MIDDLEWARE = ["django_structlog.middlewares.RequestMiddleware"]

#
# FORMATTERS
#

JSON_FORMATTER = {
    "()": structlog.stdlib.ProcessorFormatter,
    "processor": structlog.processors.JSONRenderer(),
    # structlog - foreign_pre_chain handles logs coming from stdlib logging module,
    # while the `structlog.configure` call handles everything coming from structlog.
    # They are mutually exclusive.
    "foreign_pre_chain": [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        drop_user_agent_in_dev,
        add_open_telemetry_spans,
        structlog.stdlib.PositionalArgumentsFormatter(),
    ],
}

PLAIN_CONSOLE_FORMATTER = {
    "()": structlog.stdlib.ProcessorFormatter,
    "processor": structlog.dev.ConsoleRenderer(),
    "foreign_pre_chain": [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        drop_user_agent_in_dev,
        add_open_telemetry_spans,
        structlog.stdlib.PositionalArgumentsFormatter(),
    ],
}

LOGGING_FORMATTERS = {
    "json": JSON_FORMATTER,
    "plain_console": PLAIN_CONSOLE_FORMATTER,
}
"""
Logging formatters configuration for the ``LOGGING["formatters"]`` setting.

The ``json`` formatter will produce actual JSON output and is recommended for production
deployments. The ``plain_console`` formatter is better readable for humans and
recommended in development environments.
"""

#
# Structlog configuration
#


def structlog_configure_defaults(format_exc_info: bool = True) -> None:
    """
    Configure the structlog pipeline itself.

    This is an opinionated implemention of the ``structlog.configure`` installation
    step in the structlog documentation. Call ``structlog_configure_default()`` instead
    of it in your project.
    """
    exception_processors = (
        [structlog.processors.format_exc_info] if format_exc_info else []
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            drop_user_agent_in_dev,
            add_open_telemetry_spans,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            *exception_processors,
            structlog.processors.UnicodeDecoder(),
            # structlog.processors.ExceptionPrettyPrinter(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
