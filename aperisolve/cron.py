"""RQ cron configuration.

Started by the ``cron`` compose service:

    rq cron aperisolve.cron --url redis://redis:6379/0

Jobs registered here are enqueued on the ``default`` queue at their interval
and executed by the regular worker container.
"""

from rq import cron

from .config import CLEANUP_INTERVAL_SECONDS, JOB_TIMEOUT
from .tasks import cleanup_job

cron.register(
    cleanup_job,
    queue_name="default",
    interval=CLEANUP_INTERVAL_SECONDS,
    job_timeout=JOB_TIMEOUT,
)
