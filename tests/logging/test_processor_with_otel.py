import importlib.util
from copy import deepcopy

import pytest
import structlog

from maykin_common.logging.processors import add_open_telemetry_spans

_test_logger = structlog.stdlib.get_logger("tests")


def _dependency_installed(dependency: str):
    module = importlib.util.find_spec(dependency)
    return module is not None


@pytest.fixture
def span_exporter():
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    return InMemorySpanExporter()


@pytest.fixture(autouse=True)
def reset_span_exporter(span_exporter):
    """Automatically clear span exporter after each test"""
    yield
    span_exporter.clear()


@pytest.fixture
def tracer_provider(span_exporter):
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    return provider


@pytest.mark.skipif(
    not _dependency_installed("opentelemetry"),
    reason="The 'otel' extra is not installed",
)
def test_otel_spans_processor_in_recording_mode(tracer_provider):
    tracer = tracer_provider.get_tracer("maykin_common_tests")
    event_dict = {"event": "something_happened"}

    with tracer.start_as_current_span("some-span"):
        updated_event_dict = add_open_telemetry_spans(
            _test_logger, "irrelevant", deepcopy(event_dict)
        )

    assert len(updated_event_dict["span_id"]) == 16
    assert len(updated_event_dict["trace_id"]) == 32


@pytest.mark.skipif(
    not _dependency_installed("opentelemetry"),
    reason="The 'otel' extra is not installed",
)
def test_otel_spans_processor_in_recording_mode_with_parent_span(tracer_provider):
    tracer = tracer_provider.get_tracer("maykin_common_tests")
    event_dict = {"event": "something_happened"}

    with (
        tracer.start_as_current_span("some-span"),
        tracer.start_as_current_span("nested-span"),
    ):
        updated_event_dict = add_open_telemetry_spans(
            _test_logger, "irrelevant", deepcopy(event_dict)
        )

    assert len(updated_event_dict["span_id"]) == 16
    assert len(updated_event_dict["parent_span_id"]) == 16
    assert len(updated_event_dict["trace_id"]) == 32


@pytest.mark.skipif(
    not _dependency_installed("opentelemetry"),
    reason="The 'otel' extra is not installed",
)
def test_otel_spans_processor_not_in_recording_mode():
    event_dict = {"event": "something_happened"}

    updated_event_dict = add_open_telemetry_spans(
        _test_logger, "irrelevant", deepcopy(event_dict)
    )

    assert "span_id" not in updated_event_dict
    assert "trace_id" not in updated_event_dict
