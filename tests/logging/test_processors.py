import importlib.util
from copy import deepcopy

import pytest
import structlog
from structlog.typing import EventDict

from maykin_common.logging.processors import (
    add_open_telemetry_spans,
    drop_user_agent_in_dev,
)

_test_logger = structlog.stdlib.get_logger("tests")


def _dependency_installed(dependency: str):
    module = importlib.util.find_spec(dependency)
    return module is not None


@pytest.mark.parametrize(
    "event_dict",
    [
        {"event": "request_started"},
        {"user_agent": "definitely-not-curl"},
        {"user_agent": "definitely-not-curl", "other_key": "yeppers"},
    ],
)
def test_do_not_drop_useragent(settings, event_dict: EventDict):
    settings.DEBUG = False

    updated_event_dict = drop_user_agent_in_dev(
        _test_logger, "irrelevant", deepcopy(event_dict)
    )

    assert updated_event_dict == event_dict


@pytest.mark.parametrize(
    "event_dict",
    [
        {"event": "request_started"},
        {"user_agent": "definitely-not-curl"},
        {"user_agent": "definitely-not-curl", "other_key": "yeppers"},
    ],
)
def test_do_drop_useragent(settings, event_dict: EventDict):
    settings.DEBUG = True

    updated_event_dict = drop_user_agent_in_dev(
        _test_logger, "irrelevant", deepcopy(event_dict)
    )

    assert "user_agent" not in updated_event_dict
    event_dict.pop("user_agent", None)
    assert updated_event_dict == event_dict


@pytest.mark.skipif(
    _dependency_installed("opentelemetry"),
    reason="The 'otel' extra seems to be installed",
)
def test_otel_spans_processor_does_not_crash_without_opentelemetry_installed():
    event_dict = {"event": "something_happened"}

    updated_event_dict = add_open_telemetry_spans(
        _test_logger, "irrelevant", deepcopy(event_dict)
    )

    assert updated_event_dict == event_dict
