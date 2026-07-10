from .models import Team, UserProfile


def role_display(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    if user.is_superuser:
        return {"topbar_role_label": "Super Admin"}
    profile = getattr(user, "profile", None)
    if not profile:
        return {"topbar_role_label": "Student"}
    if profile.role == UserProfile.Role.TRAINER:
        return {"topbar_role_label": "Trainer"}
    if profile.role in {UserProfile.Role.SUPER_ADMIN, UserProfile.Role.SUB_ADMIN}:
        return {"topbar_role_label": profile.get_role_display()}
    labels = ["Student"]
    if profile.role == UserProfile.Role.CAPTAIN or Team.objects.filter(captain=user).exists():
        labels.append("Captain")
    if profile.role == UserProfile.Role.VICE_CAPTAIN or Team.objects.filter(vice_captain=user).exists():
        labels.append("Vice Captain")
    if profile.role == UserProfile.Role.COORDINATOR or Team.objects.filter(coordinator=user).exists():
        labels.append("Coordinator")
    return {"topbar_role_label": " | ".join(labels)}
