"""Background maintenance jobs executed by the RQ cron scheduler."""

from .app import create_app, run_cleanup_with_lock
from .utils.sentry import initialize_sentry


def cleanup_job() -> None:
    """Run the retention sweep off the request path (see aperisolve/cron.py)."""
    initialize_sentry()
    app = create_app()
    with app.app_context():
        run_cleanup_with_lock(app)
