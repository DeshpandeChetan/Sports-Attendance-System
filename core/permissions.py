from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import AttendanceDelegate, UserProfile


ADMIN_ROLES = {UserProfile.Role.SUPER_ADMIN, UserProfile.Role.SUB_ADMIN}
TRAINER_ROLES = {UserProfile.Role.TRAINER, UserProfile.Role.COORDINATOR}
TAKER_ROLES = {
    UserProfile.Role.SUPER_ADMIN,
    UserProfile.Role.SUB_ADMIN,
    UserProfile.Role.TRAINER,
    UserProfile.Role.CAPTAIN,
    UserProfile.Role.VICE_CAPTAIN,
    UserProfile.Role.COORDINATOR,
}


def role_for(user):
    if not user.is_authenticated:
        return None
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile.role


def is_admin_user(user):
    return user.is_superuser or role_for(user) in ADMIN_ROLES


def can_manage_team(user, team):
    if is_admin_user(user):
        return True
    return role_for(user) in TRAINER_ROLES and user == team.coordinator


def can_schedule_session(user, team):
    return is_admin_user(user) or (role_for(user) in TRAINER_ROLES and user == team.coordinator)


def can_take_attendance(user, session):
    if is_admin_user(user):
        return True
    if role_for(user) in TRAINER_ROLES and user == session.team.coordinator:
        return True
    if user in {session.team.captain, session.team.vice_captain}:
        return True
    return AttendanceDelegate.objects.filter(session=session, assigned_to=user).exists()


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser or role_for(request.user) in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "You do not have permission to access that page.")
            return redirect("dashboard")

        return wrapper

    return decorator
