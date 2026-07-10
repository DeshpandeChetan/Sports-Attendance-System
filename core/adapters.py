from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import LoginAccessRequest, UserProfile


class ChristGoogleAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        email = (sociallogin.user.email or "").lower()
        full_name = " ".join(part for part in [sociallogin.user.first_name, sociallogin.user.last_name] if part).strip()
        allowed_domains = [domain.lower() for domain in settings.ALLOWED_GOOGLE_EMAIL_DOMAINS]
        if allowed_domains and not any(email.endswith(f"@{domain}") for domain in allowed_domains):
            messages.error(request, "Please sign in with your Christ University Google account.")
            return False
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
            return False
        if not created and full_name and access_request.full_name != full_name:
            access_request.full_name = full_name
            access_request.save(update_fields=["full_name", "updated_at"])
        messages.warning(request, "Your login request has been sent to the Sports Department admin. You can sign in after approval.")
        return False

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        if not get_user_model().objects.exclude(pk=user.pk).exists():
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["is_staff", "is_superuser"])
            user.profile.role = UserProfile.Role.SUPER_ADMIN
            user.profile.save(update_fields=["role", "updated_at"])
        return user
