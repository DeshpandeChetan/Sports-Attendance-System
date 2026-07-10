from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import LoginAccessRequest, UserProfile


def is_allowed_google_email(email, allowed_domains):
    email_domain = email.rsplit("@", 1)[-1].strip().lower() if "@" in email else ""
    for domain in allowed_domains:
        domain = domain.strip().lower()
        if email_domain == domain or email_domain.endswith(f".{domain}"):
            return True
    return False


class ChristGoogleAccountAdapter(DefaultSocialAccountAdapter):
    def _email_details(self, sociallogin):
        email = (sociallogin.user.email or "").strip().lower()
        full_name = " ".join(part for part in [sociallogin.user.first_name, sociallogin.user.last_name] if part).strip()
        return email, full_name

    def _validate_university_email(self, request, email):
        allowed_domains = [domain.lower() for domain in settings.ALLOWED_GOOGLE_EMAIL_DOMAINS]
        if allowed_domains and not is_allowed_google_email(email, allowed_domains):
            messages.error(request, "Please sign in with your Christ University Google account.")
            raise ImmediateHttpResponse(redirect("login"))

    def pre_social_login(self, request, sociallogin):
        email, _ = self._email_details(sociallogin)
        self._validate_university_email(request, email)
        user = get_user_model().objects.filter(email__iexact=email).first()
        if user and not user.is_active:
            messages.error(request, "Your account is deactivated. Please contact the Sports Department admin.")
            raise ImmediateHttpResponse(redirect("login"))
        if user and not sociallogin.is_existing:
            sociallogin.connect(request, user)
            sociallogin.user = user

    def is_open_for_signup(self, request, sociallogin):
        email, full_name = self._email_details(sociallogin)
        self._validate_university_email(request, email)
        if not get_user_model().objects.exists():
            return True
        if get_user_model().objects.filter(email__iexact=email).exists():
            return True
        access_request, created = LoginAccessRequest.objects.get_or_create(
            email=email,
            defaults={"full_name": full_name, "status": LoginAccessRequest.Status.PENDING},
        )
        if access_request.status == LoginAccessRequest.Status.APPROVED:
            return True
        if access_request.status == LoginAccessRequest.Status.REJECTED:
            messages.error(request, "Your sports attendance login request was rejected. Please contact the Sports Department.")
            raise ImmediateHttpResponse(redirect("login"))
        if not created and full_name and access_request.full_name != full_name:
            access_request.full_name = full_name
            access_request.save(update_fields=["full_name", "updated_at"])
        messages.warning(
            request,
            "First login? Your account requires admin approval before access is granted.",
        )
        raise ImmediateHttpResponse(redirect("login"))

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        if not get_user_model().objects.exclude(pk=user.pk).exists():
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["is_staff", "is_superuser"])
            user.profile.role = UserProfile.Role.SUPER_ADMIN
            user.profile.save(update_fields=["role", "updated_at"])
        return user
