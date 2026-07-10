from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError

from allauth.socialaccount.models import SocialApp

from core.google_oauth import load_google_client_secret


class Command(BaseCommand):
    help = "Import Google OAuth client_secret.json into django-allauth SocialApp."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=settings.BASE_DIR / "client_secret.json",
            help="Path to Google OAuth client_secret.json.",
        )
        parser.add_argument(
            "--site-domain",
            default="127.0.0.1:8000",
            help="Site domain to attach to the Google SocialApp.",
        )
        parser.add_argument(
            "--site-name",
            default="Sports Attendance System",
            help="Site display name.",
        )

    def handle(self, *args, **options):
        try:
            google_config = load_google_client_secret(options["path"])
        except FileNotFoundError as exc:
            raise CommandError(f"File not found: {options['path']}") from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        site, _ = Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={"domain": options["site_domain"], "name": options["site_name"]},
        )
        app, created = SocialApp.objects.update_or_create(
            provider="google",
            name="Google",
            defaults={
                "client_id": google_config["client_id"],
                "secret": google_config["client_secret"],
                "key": "",
                "settings": {
                    "project_id": google_config["project_id"],
                    "auth_uri": google_config["auth_uri"],
                    "token_uri": google_config["token_uri"],
                    "auth_provider_x509_cert_url": google_config["auth_provider_x509_cert_url"],
                    "redirect_uris": google_config["redirect_uris"],
                },
            },
        )
        app.sites.set([site])
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} Google SocialApp for {site.domain}."))
