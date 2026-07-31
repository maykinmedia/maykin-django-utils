"""
Command line companion to the ``maykin-common`` Django utilities.

The command line script is deliberately written in pure Python without loading Django
at all (for performance), as opposed to providing Django management commands. Large
Django projects may see slow startup times in the order of 2-10s due to (expensive)
imports when loading all the code. This pairs very badly with health checks machinery
which tend to have timeouts of a couple of seconds.
"""

import importlib.metadata
import socket
import sys
import time
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse, urlunparse

import requests
import typer

app = typer.Typer()

_WORKER_EXIT_CODE_EVENT_LOOP_BROKEN = 1
_WORKER_EXIT_CODE_PING_FAILURE = 2
_WORKER_EXIT_CODE_NOT_READY = 4


@app.command()
def version():
    version = importlib.metadata.version("maykin_common")
    typer.echo(f"maykin-common v{version}")


@app.command(name="health-check")
def health_check(
    endpoint: Annotated[
        str,
        typer.Option(help="Endpoint/path to test for connection and status code."),
    ] = "/_healthz/livez/",
    timeout: Annotated[
        int,
        typer.Option(help="Timeout for the GET request (in seconds)."),
    ] = 3,
):
    """
    Execute an HTTP health check call against the provided endpoint.

    If no host or domain is provided with the ``endpoint`` option, a default of
    ``http://localhost:8000`` will be used.
    """

    # URLs must start with a scheme, otherwise urlparse chokes :-)
    if not (endpoint.startswith(("http://", "https://"))):
        endpoint = f"http://{endpoint}"

    parsed = urlparse(endpoint)
    normalized_url = urlunparse(
        (
            parsed.scheme,
            parsed.netloc or "localhost:8000",
            parsed.path or "/_healthz/livez/",
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )

    try:
        response = requests.get(normalized_url, timeout=timeout)
    except requests.RequestException as exc:
        typer.secho(f"DOWN ({exc.__class__.__name__})", fg=typer.colors.RED, err=True)
        sys.exit(1)

    if up := response.ok:
        typer.secho(
            f"UP, response status code: {response.status_code}",
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            f"DOWN, response status code: {response.status_code}",
            fg=typer.colors.RED,
            err=True,
        )

    exit_code = 0 if up else 1
    sys.exit(exit_code)


@app.command(name="worker-health-check")
def worker_health_check(
    # liveness
    liveness_file: Annotated[
        Path,
        typer.Option(
            help="The event loop liveness file, created and updated by the "
            "`EventLoopProbe`."
        ),
    ] = Path("/tmp") / "celery_worker_event_loop_live",
    max_age: Annotated[
        int,
        typer.Option(
            help="How long ago the last update of the event loop liveness file is "
            "allowed to be, in seconds. You should match this to the "
            "'MKN_HEALTH_CHECKS_WORKER_EVENT_LOOP_PROBE_FREQUENCY_SECONDS' setting."
        ),
    ] = 60 + 10,
    skip_event_loop_liveness: Annotated[
        bool,
        typer.Option(
            help="Opt-out from the event loop liveness check.",
        ),
    ] = False,
    broker: Annotated[
        str,
        typer.Option(
            help="Broker URL, should match the 'CELERY_BROKER' setting. Used for the "
            "ping roundtrip check."
        ),
    ] = "redis://localhost:6379/0",
    worker_name: Annotated[
        str,
        typer.Option(
            envvar="CELERY_WORKER_NAME",
            help="Worker name, typically composed from <queue>@<host>.",
        ),
    ] = f"celery@{socket.gethostname()}",
    ping_timeout: Annotated[
        int, typer.Option(help="Timeout in seconds after which the ping check fails.")
    ] = 3,
    skip_ping: Annotated[
        bool, typer.Option(help="Opt-out from the ping roundtrip check.")
    ] = False,
    # readiness
    readiness_file: Annotated[
        Path,
        typer.Option(
            help="The readiness file, created when the worker is ready to process "
            "tasks."
        ),
    ] = Path("/tmp") / "celery_worker_ready",
    skip_readiness: Annotated[
        bool, typer.Option(help="Opt-in to the readiness check.")
    ] = True,
):
    """
    Run health checks for the Celery worker.

    The worker health checks consist of separate components. The defaults are geared
    towards liveness checks, but you can disable/enable parts to adapt to your
    situation.

    * Check the `liveness-file` to detect issues in the worker event loop. If the event
      loop is broken, the worker will definitely not be processing tasks and a restart
      is necessary.
    * Ping the worker using Celery's inspection machinery. Pinging verifies the broker
      connection, as it performs a complete roundtrip. Broker connection loss can
      sometimes be solved by restarting the worker.
    * Check the presence of the `readiness-file`. Absence of the readiness file
      indicates the worker is not (yet) ready to process tasks. It may have been stopped
      or is still starting up.

    If any check fails, the command exist with a non-zero exit code.
    """
    # always instantiate an app as a sanity check
    try:
        from celery import Celery
    except ImportError:  # pragma: no cover
        typer.secho(
            "Could not import celery - please make sure to execute this in a celery"
            "worker environment.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(1)

    celery_app = Celery(broker=broker)

    if not skip_event_loop_liveness:
        if not liveness_file.exists() or not liveness_file.is_file():
            typer.secho(
                f"File '{liveness_file}' does not exist or is not a file.",
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(_WORKER_EXIT_CODE_EVENT_LOOP_BROKEN)

        now = time.time()
        last_modified = liveness_file.stat().st_mtime
        age_in_seconds = int(now - last_modified)
        if age_in_seconds > max_age:
            typer.secho(
                f"File '{liveness_file}' is older than max-age.",
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(_WORKER_EXIT_CODE_EVENT_LOOP_BROKEN)
        else:
            typer.secho(
                "The event loop appears to be running.",
                fg=typer.colors.GREEN,
            )

    if not skip_ping:
        replies = celery_app.control.ping(
            destination=[worker_name], timeout=ping_timeout
        )
        if replies:
            typer.secho(f"{worker_name}: PONG.", fg=typer.colors.GREEN)
        else:
            typer.secho(
                f"No reply to ping from '{worker_name}' after {ping_timeout}s.",
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(_WORKER_EXIT_CODE_PING_FAILURE)

    if not skip_readiness:
        if not readiness_file.exists() or not readiness_file.is_file():
            typer.secho(
                f"File '{readiness_file}' does not exist - worker is not ready.",
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(_WORKER_EXIT_CODE_NOT_READY)
        else:
            typer.secho(
                "The worker appears ready to process tasks.",
                fg=typer.colors.GREEN,
            )

    sys.exit(0)


@app.command(name="beat-health-check")
def beat_health_check(
    file: Annotated[
        Path,
        typer.Option(
            help="The liveness file, created and updated by the Beat health check "
            "machinery."
        ),
    ] = Path("/tmp") / "celery_beat_live",
    max_age: Annotated[
        int,
        typer.Option(
            help="How long ago the last update of liveness file is allowed to be, in "
            "seconds. You should tune this to the beat schedule of your application."
        ),
    ] = 3600,
):
    """
    Check the last modified timestamp of the Beat liveness file.

    If it's older than ``max-age``, Beat is considered unhealthy.
    """
    file = file.resolve()
    if not file.exists() or not file.is_file():
        typer.secho(
            f"File '{file}' does not exist or is not a file.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(1)

    # check the file age
    now = time.time()
    last_modified = file.stat().st_mtime
    age_in_seconds = int(now - last_modified)
    if age_in_seconds > max_age:
        typer.secho(
            f"File '{file}' is older than max-age.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(1)
    else:
        human_readable_age: str = f"{age_in_seconds}s"
        if 60 < age_in_seconds < 3600:
            age_in_minutes = round(age_in_seconds / 60, 1)
            human_readable_age = f"{age_in_minutes:.1f}m".replace(".0", "")
        elif age_in_seconds >= 3600:
            age_in_hours = round(age_in_seconds / 3600, 1)
            human_readable_age = f"{age_in_hours:.1f}h".replace(".0", "")

        typer.secho(
            f"Last scheduled task: {human_readable_age} ago.",
            fg=typer.colors.GREEN,
        )
        sys.exit(0)


if __name__ == "__main__":  # pragma: no cover
    app()
