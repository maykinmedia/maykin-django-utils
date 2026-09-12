"""
Custom processors for structlog.

Maykin projects use ``structlog`` and the Django integration to get structured logging.
The processors here target our particular combination of observability instrumentation.
"""

import importlib.util

from django.conf import settings

from structlog.typing import EventDict, WrappedLogger

_HAS_OTEL = importlib.util.find_spec("opentelemetry") is not None


def drop_user_agent_in_dev(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    if settings.DEBUG and "user_agent" in event_dict:
        del event_dict["user_agent"]
    return event_dict


def add_open_telemetry_spans(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add trace and span IDs to the structlog event dict when tracing is active.

    Note that tracing is not active/recording when OTEL_SDK_DISABLED=true is set,
    which is why coverage reporting is disabled on this processor.

    Implementation adapted from the docs:
    https://www.structlog.org/en/stable/frameworks.html#opentelemetry
    """
    if not _HAS_OTEL:
        return event_dict

    # local import because OTel is an optional dependency!
    from opentelemetry import trace

    span = trace.get_current_span()
    if not span.is_recording():
        return event_dict

    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)

    # emit the attributes as top-level key, see the OTel data model:
    # https://opentelemetry.io/docs/concepts/signals/logs/#log-record
    event_dict.update(
        {
            "span_id": format(ctx.span_id, "016x"),
            "trace_id": format(ctx.trace_id, "032x"),
        }
    )
    if parent:
        event_dict["parent_span_id"] = format(parent.span_id, "016x")

    return event_dict
