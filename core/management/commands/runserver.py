import logging
import threading

from django.conf import settings
from django.contrib.staticfiles.management.commands.runserver import Command as DjangoRunserverCommand

from core.email_worker import run_email_worker


logger = logging.getLogger(__name__)
_worker_guard = threading.Lock()
_active_worker = None


class Command(DjangoRunserverCommand):
    """Development server with one in-process email queue worker."""

    def inner_run(self, *args, **options):
        global _active_worker
        stop_event = threading.Event()
        owns_worker = False
        with _worker_guard:
            if not _active_worker or not _active_worker.is_alive():
                _active_worker = threading.Thread(
                    target=run_email_worker,
                    kwargs={"stop_event": stop_event},
                    name="email-notification-worker",
                    daemon=True,
                )
                _active_worker.start()
                owns_worker = True
                logger.info("Automatic email worker started with Django development server.")
        try:
            return super().inner_run(*args, **options)
        finally:
            if owns_worker:
                stop_event.set()
                _active_worker.join(timeout=getattr(settings, "EMAIL_TIMEOUT", 15) + 2)
                with _worker_guard:
                    _active_worker = None
                logger.info("Automatic email worker stopped with Django development server.")
