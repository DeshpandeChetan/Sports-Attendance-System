from django.core.management.base import BaseCommand
from core.email_worker import run_email_worker


class Command(BaseCommand):
    help = "Process queued notification emails outside web requests."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process currently available jobs and exit.")
        parser.add_argument("--interval", type=float, default=2.0, help="Seconds between queue checks.")

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Email notification worker started."))
        run_email_worker(once=options["once"], interval=options["interval"])
