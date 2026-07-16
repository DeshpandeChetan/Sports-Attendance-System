from .models import Team, UserProfile


def breadcrumbs(request):
    match = getattr(request, "resolver_match", None)
    url_name = getattr(match, "url_name", "") if match else ""
    labels = {
        "dashboard": "Dashboard",
        "analytics": "Analytics",
        "sports": "Sports",
        "teams": "Teams",
        "members": "Add Students",
        "member_detail": "Student Details",
        "trainers": "Add Trainer",
        "venues": "Venues",
        "settings": "Settings",
        "sessions": "Schedule Practice",
        "attendance_detail": "Attendance Details",
        "take_attendance": "Take Attendance",
        "delegate_attendance": "Assign Session Incharge",
        "my_attendance": "My Attendance",
        "my_profile": "My Profile",
        "feedback": "Feedback",
        "reports": "Reports",
    }
    if not request.user.is_authenticated:
        return {}
    if url_name == "dashboard":
        return {"breadcrumb_items": []}
    return {"breadcrumb_items": [{"label": "Dashboard", "url_name": "dashboard"}, {"label": labels.get(url_name, "Page")}]}


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
