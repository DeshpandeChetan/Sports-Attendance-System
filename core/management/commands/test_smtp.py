import smtplib
import socket

from django.conf import settings
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Test configured SMTP connectivity and authentication without sending email."

    def handle(self, *args, **options):
        self.stdout.write(
            f"Testing SMTP authentication to {settings.EMAIL_HOST}:{settings.EMAIL_PORT} "
            f"(TLS={settings.EMAIL_USE_TLS}, SSL={settings.EMAIL_USE_SSL}, "
            f"username configured={bool(settings.EMAIL_HOST_USER)}, "
            f"password configured={bool(settings.EMAIL_HOST_PASSWORD)})"
        )
        # Deliberately force the SMTP backend: DEBUG normally uses the console
        # backend, but this command exists to validate real SMTP authentication.
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            fail_silently=False,
        )
        try:
            connection.open()
        except smtplib.SMTPAuthenticationError as exc:
            detail = exc.smtp_error.decode(errors="replace") if isinstance(exc.smtp_error, bytes) else str(exc.smtp_error)
            raise CommandError(
                f"SMTP authentication rejected ({exc.smtp_code}: {detail}). The connection and TLS handshake "
                "worked, but the SMTP provider rejected the login. Check the sender address, app password, "
                "and whether SMTP access is permitted for this account."
            ) from None
        except (socket.timeout, TimeoutError) as exc:
            raise CommandError(f"SMTP connection timed out: {exc}") from None
        except (socket.gaierror, ConnectionError, OSError, smtplib.SMTPException) as exc:
            raise CommandError(f"SMTP connection failed ({type(exc).__name__}): {exc}") from None
        else:
            self.stdout.write(self.style.SUCCESS("SMTP connection, TLS negotiation, and authentication succeeded. No email was sent."))
        finally:
            try:
                connection.close()
            except Exception:
                pass
