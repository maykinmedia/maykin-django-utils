import atexit
import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from celery import bootsteps
from celery.apps.worker import Worker as _Worker
from celery.beat import Service as BeatService
from celery.signals import after_task_publish, beat_init, worker_ready, worker_shutdown
from celery.worker.consumer import Consumer
from kombu.asynchronous.timer import Entry as TimerEntry, Timer

from maykin_common.settings import get_setting

logger = logging.getLogger(__name__)

if TYPE_CHECKING:

    class Worker(_Worker):
        """
        Worker class with timer attribute.

        Assigned through :meth:`celery.worker.components.Timer.create`, it's a dynamic
        attribute that's not present in the base class definitions, so we have to
        massage it a bit.
        """

        timer: Timer
else:
    Worker = _Worker


#
# Utilities for checking the health of celery worker
#


class EventLoopProbe(bootsteps.StartStopStep):
    """
    Checks that the Celery worker event loop is alive.

    When the Celery worker starts, it starts the event loop, timer and processing pool.
    As a "final" step, it starts the Consumer blueprint, which is responsible for
    establishing the broker connection and actually start processing/consuming messages
    and tasks.

    This event loop probe installs a bootstep when the timer is available, and schedules
    a periodic callback that touches a liveness file. If the timestamp of the last
    modified moment of the liveness file is too long again, we can conclude/assume that
    the event loop has crashed and the worker should be restarted, as it's likely that
    ETA/countdown tasks and tasks in general are not being processed anymore by this
    worker. This makes no guarantees about actually being able to consume tasks or a
    live connection though. The timer runs in the main worker process (when using
    the preforking/multi-processing pool).

    Celery itself *should* re-establish broker connection on connection loss, by
    restarting the Consumer blueprint, but bugs in Celery itself have been observed in
    the past. We can implement connectivity checks by pinging the worker from itself,
    which is set up elsewhere.

    See the `upstream <https://docs.celeryq.dev/en/stable/userguide/extending.html#blueprints>`_
    documentation for details about blueprints and bootstep mechanisms.

    Usage::

        >>> app = Celery("my-project")
        >>> app.steps["worker"].add(EventLoopProbe)
    """

    # we need the Timer component before we can run this bootstep. Celery uses this to
    # figure out the step dependency graph.
    requires: ClassVar[set[str]] = {"celery.worker.components:Timer"}
    tref: TimerEntry | None = None
    liveness_file: Path

    def start(self, parent: Worker):
        self.liveness_file = liveness_file = get_setting(
            "MKN_HEALTH_CHECKS_WORKER_EVENT_LOOP_LIVENESS_FILE"
        )
        # create intermediate directories if they don't yet exist
        if not (parent_dir := liveness_file.parent).exists():
            parent_dir.mkdir(parents=True, exist_ok=True)

        liveness_file.touch()
        frequency: int = get_setting(
            "MKN_HEALTH_CHECKS_WORKER_EVENT_LOOP_PROBE_FREQUENCY_SECONDS"
        )
        self.tref = parent.timer.call_repeatedly(
            frequency, liveness_file.touch, priority=10
        )

    def stop(self, parent: Worker):
        assert self.tref is not None
        self.tref.cancel()
        self.liveness_file.unlink(missing_ok=True)


def on_worker_ready(*, sender: Consumer, **kwargs):
    """
    Create/touch the readiness file when the worker is ready to accept work.
    """
    readiness_file: Path = get_setting("MKN_HEALTH_CHECKS_WORKER_READINESS_FILE")
    # create intermediate directories if they don't yet exist
    if not (parent_dir := readiness_file.parent).exists():
        parent_dir.mkdir(parents=True, exist_ok=True)
    readiness_file.touch()
    logger.info("worker_ready")


def on_worker_shutdown(*, sender: Worker, **kwargs):
    """
    Delete the readiness file when a worker shuts down.
    """
    logger.info("worker_shutdown")
    readiness_file: Path = get_setting("MKN_HEALTH_CHECKS_WORKER_READINESS_FILE")
    readiness_file.unlink(missing_ok=True)


def connect_worker_signals():
    worker_ready.connect(on_worker_ready, dispatch_uid="probes.on_worker_ready")
    worker_shutdown.connect(
        on_worker_shutdown, dispatch_uid="probes.on_worker_shutdown"
    )


#
# Utilities for checking the health of celery beat
#

_RUNNING_IN_BEAT = False


def on_beat_init(*, sender: BeatService, **kwargs):
    global _RUNNING_IN_BEAT
    _RUNNING_IN_BEAT = True
    logger.debug("beat_process_marked")
    liveness_file: Path = get_setting("MKN_HEALTH_CHECKS_BEAT_LIVENESS_FILE")
    # on shutdown, clear up the liveness file
    atexit.register(liveness_file.unlink, missing_ok=True)


def on_beat_task_published(*, sender: str, routing_key: str, **kwargs):
    """
    Update the celery beat liveness every time a task is successfully published.

    ``after_task_publish`` fires in the process that sent the task, so we must discern
    between the regular Django app that schedules tasks, and celery beat that also
    schedules tasks. We do this by tapping into the ``beat_init`` signal to mark the
    process as a beat process, and only touch the liveness file when running in beat.
    """
    if not _RUNNING_IN_BEAT:
        return

    liveness_file: Path = get_setting("MKN_HEALTH_CHECKS_BEAT_LIVENESS_FILE")
    logger.debug(
        "beat_task_published", extra={"task": sender, "routing_key": routing_key}
    )
    # create intermediate directories if they don't yet exist
    if not (parent_dir := liveness_file.parent).exists():
        parent_dir.mkdir(parents=True, exist_ok=True)
    # touching the file updates the last modified timestamp, which can be checked by
    # the health-check command
    liveness_file.touch()


def connect_beat_signals():
    # register signals for beat so that we can health-check it
    beat_init.connect(on_beat_init, dispatch_uid="probes.on_beat_init")
    after_task_publish.connect(
        on_beat_task_published, dispatch_uid="probes.on_beat_task_published"
    )
