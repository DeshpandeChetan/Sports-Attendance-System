import logging
import threading
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import close_old_connections, transaction
from django.utils import timezone

from .email_notifications import send_notification_emails
from .models import EmailNotificationJob


logger = logging.getLogger(__name__)
User = get_user_model()
MAX_ATTEMPTS = 3


def recover_interrupted_jobs():
    stale_before = timezone.now() - timedelta(minutes=10)
    return EmailNotificationJob.objects.filter(
        status=EmailNotificationJob.Status.PROCESSING,
        updated_at__lt=stale_before,
    ).update(status=EmailNotificationJob.Status.PENDING, next_attempt_at=timezone.now())


def process_one_email_job():
    with transaction.atomic():
        job = (
            EmailNotificationJob.objects.select_for_update()
            .filter(status=EmailNotificationJob.Status.PENDING, next_attempt_at__lte=timezone.now())
            .first()
        )
        if not job:
            return False
        job.status = EmailNotificationJob.Status.PROCESSING
        job.attempts += 1
        job.save(update_fields=["status", "attempts", "updated_at"])

    try:
        users = list(User.objects.filter(pk__in=job.recipient_user_ids, is_active=True))
        result = send_notification_emails(users, job.notification_type, job.context)
        failed_ids = result["failed_user_ids"]
        if failed_ids:
            job.recipient_user_ids = failed_ids
            job.last_error = f"Delivery failed for {len(failed_ids)} recipient(s); see SMTP logs."
            if job.attempts >= MAX_ATTEMPTS:
                job.status = EmailNotificationJob.Status.FAILED
                job.processed_at = timezone.now()
            else:
                job.status = EmailNotificationJob.Status.PENDING
                job.next_attempt_at = timezone.now() + timedelta(minutes=2 ** (job.attempts - 1))
        else:
            job.status = EmailNotificationJob.Status.SENT
            job.last_error = ""
            job.processed_at = timezone.now()
        job.save()
    except Exception as exc:
        job.last_error = f"{type(exc).__name__}: {exc}"[:2000]
        job.status = EmailNotificationJob.Status.FAILED if job.attempts >= MAX_ATTEMPTS else EmailNotificationJob.Status.PENDING
        job.next_attempt_at = timezone.now() + timedelta(minutes=2 ** (job.attempts - 1))
        if job.status == EmailNotificationJob.Status.FAILED:
            job.processed_at = timezone.now()
        job.save()
        logger.exception("Email job %s failed.", job.pk)
    return True


def run_email_worker(stop_event=None, interval=2.0, once=False):
    stop_event = stop_event or threading.Event()
    close_old_connections()
    try:
        recovered = recover_interrupted_jobs()
        if recovered:
            logger.warning("Recovered %s interrupted email job(s).", recovered)
        logger.info("Email notification worker started.")
        while not stop_event.is_set():
            try:
                processed = process_one_email_job()
            except Exception:
                logger.exception("Email worker queue check failed.")
                processed = False
            if not processed:
                if once:
                    break
                stop_event.wait(max(interval, 0.2))
    finally:
        close_old_connections()
        logger.info("Email notification worker stopped.")
