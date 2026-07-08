"""Background maintenance jobs executed by the RQ cron scheduler."""

from .app import create_app, run_cleanup_with_lock
from .models import cleanup_old_entries
from .utils.sentry import initialize_sentry


def cleanup_job() -> None:
    """Run the retention sweep off the request path (see aperisolve/cron.py)."""
    initialize_sentry()
    app = create_app()
    with app.app_context():
        run_cleanup_with_lock(app)


def cleanup_sweep_job() -> None:
    """Run the retention sweep unconditionally.

    Enqueued from the request path by ``schedule_cleanup`` (issue #191), which
    already holds the interval lock, so this must not re-claim it.
    """
    initialize_sentry()
    app = create_app()
    with app.app_context():
        cleanup_old_entries()
