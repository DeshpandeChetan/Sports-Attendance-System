from django.conf import settings


INVALID_CHRIST_EMAIL_MESSAGE = "Please sign in with your Christ University Google account."


def is_allowed_christ_email(email):
    email = str(email or "").strip().lower()
    if "@" not in email:
        return False
    domain = email.rsplit("@", 1)[-1]
    allowed_domains = [
        str(item).strip().lower()
        for item in getattr(settings, "ALLOWED_GOOGLE_EMAIL_DOMAINS", ["christuniversity.in"])
        if str(item).strip()
    ] or ["christuniversity.in"]
    return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in allowed_domains)


def validate_christ_email(email):
    if not is_allowed_christ_email(email):
        raise ValueError(INVALID_CHRIST_EMAIL_MESSAGE)
    return str(email or "").strip().lower()
