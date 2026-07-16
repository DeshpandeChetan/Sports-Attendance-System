import re
from datetime import timedelta
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from allauth.socialaccount.models import SocialApp

from .forms import (
    AttendanceEditForm,
    DelegateForm,
    FeedbackForm,
    MembershipForm,
    ProfileForm,
    ReportFilterForm,
    SessionFeedbackForm,
    SessionForm,
    SportForm,
    TeamForm,
    VenueForm,
)
from .models import (
    AttendanceDelegate,
    AttendanceEditLog,
    AttendanceRecord,
    Feedback,
    LoginAccessRequest,
    Membership,
    Session,
    Sport,
    Team,
    UserProfile,
    Venue,
)
from .permissions import ADMIN_ROLES, TRAINER_ROLES, can_manage_team, can_schedule_session, can_take_attendance, is_admin_user, role_for, role_required

User = get_user_model()


def login_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    google_configured = SocialApp.objects.filter(provider="google", sites__id=1).exists()
    return render(request, "account/login.html", {"google_configured": google_configured})


@login_required
def dashboard(request):
    role = role_for(request.user)
    today = timezone.localdate()
    sessions = visible_sessions(request.user)
    male_teams = Team.objects.filter(gender=Team.TeamGender.MALE).count()
    female_teams = Team.objects.filter(gender=Team.TeamGender.FEMALE).count()
    student_count = User.objects.filter(profile__role=UserProfile.Role.MEMBER).count()
    trainer_count = User.objects.filter(profile__role__in=[UserProfile.Role.TRAINER, UserProfile.Role.COORDINATOR]).count()
    sport_count = Sport.objects.count()
    context = {
        "role": role,
        "today_sessions": sessions.filter(start_at__date=today)[:8],
        "upcoming_sessions": sessions.filter(start_at__date__gte=today)[:8],
        "attendance_percent": attendance_percentage(request.user),
        "unread_feedback": Feedback.objects.filter(receiver=request.user, is_read=False).count(),
        "sport_stats": Sport.objects.annotate(session_count=Count("teams__sessions")).order_by("name"),
        "admin_stats": {
            "sports": sport_count,
            "students": student_count,
            "trainers": trainer_count,
            "male_teams": male_teams,
            "female_teams": female_teams,
            "teams": male_teams + female_teams,
        },
        "dashboard_chart_data": {
            "teamGender": {"labels": ["Male Teams", "Female Teams"], "data": [male_teams, female_teams]},
            "people": {"labels": ["Students", "Trainers"], "data": [student_count, trainer_count]},
            "inventory": {"labels": ["Sports", "Teams"], "data": [sport_count, male_teams + female_teams]},
        },
    }
    return render(request, "core/dashboard.html", context)


@login_required
@role_required(*ADMIN_ROLES)
def analytics(request):
    male_teams = Team.objects.filter(gender=Team.TeamGender.MALE).count()
    female_teams = Team.objects.filter(gender=Team.TeamGender.FEMALE).count()
    student_count = User.objects.filter(profile__role=UserProfile.Role.MEMBER).count()
    trainer_count = User.objects.filter(profile__role__in=[UserProfile.Role.TRAINER, UserProfile.Role.COORDINATOR]).count()
    sport_count = Sport.objects.count()
    team_count = male_teams + female_teams
    chart_data = {
        "teamGender": {"labels": ["Male Teams", "Female Teams"], "data": [male_teams, female_teams]},
        "people": {"labels": ["Students", "Trainers"], "data": [student_count, trainer_count]},
        "inventory": {"labels": ["Sports", "Teams"], "data": [sport_count, team_count]},
    }
    return render(request, "core/analytics.html", {"dashboard_chart_data": chart_data})


def visible_sessions(user):
    qs = Session.objects.select_related("team", "team__sport")
    if is_admin_user(user):
        return qs
    return qs.filter(
        Q(team__memberships__user=user, team__memberships__is_active=True)
        | Q(team__captain=user)
        | Q(team__vice_captain=user)
        | Q(team__coordinator=user)
        | Q(delegates__assigned_to=user)
    ).distinct()


def attendance_percentage(user):
    total = AttendanceRecord.objects.filter(member=user).count()
    if total == 0:
        return None
    positive = AttendanceRecord.objects.filter(member=user, status__in=["PRESENT", "LATE", "EARLY_EXIT"]).count()
    return round((positive / total) * 100, 1)


def role_label(user):
    if not user or not user.is_authenticated:
        return ""
    if user.is_superuser:
        return "Super Admin"
    return user.profile.get_role_display()


def build_student_from_post(request, existing_user=None):
    full_name = request.POST.get("student_name", "").strip()
    email = request.POST.get("student_email", "").strip().lower()
    department = request.POST.get("department", "").strip()
    class_name = request.POST.get("class_name", "").strip()
    phone = request.POST.get("mobile_number", "").strip()
    if not email:
        raise ValueError("Student email is required.")
    if phone and not re.fullmatch(r"\d{10}", phone):
        raise ValueError("Mobile number must be exactly 10 digits.")
    user = existing_user or User.objects.filter(email__iexact=email).first()
    if user is None:
        user = User(username=email, email=email)
        user.set_unusable_password()
    if full_name:
        parts = full_name.split(" ", 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ""
    user.email = email
    user.username = email
    user.save()
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = UserProfile.Role.MEMBER
    profile.department = department
    profile.class_name = class_name
    profile.phone = phone
    profile.save(update_fields=["role", "department", "class_name", "phone", "updated_at"])
    return user


def create_student_from_access_request(access_request):
    user = User.objects.filter(email__iexact=access_request.email).first()
    if user is None:
        user = User(username=access_request.email, email=access_request.email)
        user.set_unusable_password()
    user.email = access_request.email
    user.username = access_request.email
    if access_request.full_name:
        parts = access_request.full_name.split(" ", 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ""
    user.save()
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = UserProfile.Role.MEMBER
    profile.save(update_fields=["role", "updated_at"])
    return user


@login_required
@role_required(*ADMIN_ROLES)
def sports_list(request):
    if request.method == "POST":
        action = request.POST.get("action")
        sport_id = request.POST.get("sport_id")
        sport = get_object_or_404(Sport, pk=sport_id) if sport_id else None

        if action in {"create", "update"}:
            form = SportForm(request.POST, instance=sport)
            if form.is_valid():
                form.save()
                messages.success(request, "Sport saved successfully.")
            else:
                messages.error(request, "Please correct the sport details and try again.")
        elif action == "deactivate" and sport:
            sport.is_active = False
            sport.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"{sport.name} deactivated.")
        elif action == "activate" and sport:
            sport.is_active = True
            sport.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"{sport.name} activated.")
        elif action == "delete" and sport:
            sport_name = sport.name
            sport.delete()
            messages.success(request, f"{sport_name} deleted.")
        return redirect("sports")

    sports = Sport.objects.annotate(team_count=Count("teams")).order_by("name")
    return render(request, "core/sports.html", {"sports": sports, "sport_count": sports.count()})


@login_required
@role_required(*ADMIN_ROLES)
def venues_list(request):
    if request.method == "POST":
        action = request.POST.get("action")
        venue_id = request.POST.get("venue_id")
        venue = get_object_or_404(Venue, pk=venue_id) if venue_id else None
        if action in {"create", "update"}:
            form = VenueForm(request.POST, instance=venue)
            if form.is_valid():
                form.save()
                messages.success(request, "Venue saved successfully.")
            else:
                messages.error(request, "Please correct the venue details and try again.")
        elif action == "deactivate" and venue:
            venue.is_active = False
            venue.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"{venue.name} deactivated.")
        elif action == "activate" and venue:
            venue.is_active = True
            venue.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"{venue.name} activated.")
        elif action == "delete" and venue:
            venue_name = venue.name
            venue.delete()
            messages.success(request, f"{venue_name} deleted.")
        return redirect("venues")

    venues = Venue.objects.all().order_by("name")
    return render(request, "core/venues.html", {"venues": venues})


@login_required
@role_required(*ADMIN_ROLES)
def sport_form(request, pk=None):
    sport = get_object_or_404(Sport, pk=pk) if pk else None
    form = SportForm(request.POST or None, instance=sport)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Sport saved.")
        return redirect("sports")
    return render(request, "core/form.html", {"form": form, "title": "Sport", "back_url": reverse("sports")})


@login_required
def teams_list(request):
    if is_admin_user(request.user) and request.method == "POST":
        action = request.POST.get("action")
        team_id = request.POST.get("team_id")
        team = get_object_or_404(Team, pk=team_id) if team_id else None
        if action in {"create", "update"}:
            form = TeamForm(request.POST, instance=team)
            if form.is_valid():
                form.save()
                messages.success(request, "Team saved successfully.")
            else:
                messages.error(request, "Please correct the team details and try again.")
        elif action == "deactivate" and team:
            team.is_active = False
            team.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"{team.name} deactivated.")
        elif action == "activate" and team:
            team.is_active = True
            team.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"{team.name} activated.")
        elif action == "delete" and team:
            team_name = team.name
            team.delete()
            messages.success(request, f"{team_name} deleted.")
        return redirect("teams")

    teams = Team.objects.select_related("sport", "captain", "vice_captain", "coordinator")
    if not is_admin_user(request.user):
        teams = teams.filter(Q(memberships__user=request.user) | Q(captain=request.user) | Q(vice_captain=request.user) | Q(coordinator=request.user)).distinct()
    users = User.objects.all().order_by("first_name", "last_name", "username")
    sports = Sport.objects.filter(is_active=True).order_by("name")
    return render(request, "core/teams.html", {"teams": teams, "users": users, "sports": sports})


@login_required
@role_required(*ADMIN_ROLES)
def team_form(request, pk=None):
    team = get_object_or_404(Team, pk=pk) if pk else None
    form = TeamForm(request.POST or None, instance=team)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Team saved.")
        return redirect("teams")
    return render(request, "core/form.html", {"form": form, "title": "Team", "back_url": reverse("teams")})


@login_required
def members_list(request):
    if is_admin_user(request.user) and request.method == "POST":
        action = request.POST.get("action")
        request_id = request.POST.get("request_id")
        access_request = get_object_or_404(LoginAccessRequest, pk=request_id) if request_id else None
        if action in {"approve_request", "reject_request"} and access_request:
            with transaction.atomic():
                access_request.status = LoginAccessRequest.Status.APPROVED if action == "approve_request" else LoginAccessRequest.Status.REJECTED
                access_request.reviewed_by = request.user
                access_request.reviewed_at = timezone.now()
                access_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
                if action == "approve_request":
                    create_student_from_access_request(access_request)
            message = "approved and added to Add Students" if action == "approve_request" else "rejected"
            messages.success(request, f"{access_request.email} {message}.")
            return redirect("members")

        membership_id = request.POST.get("membership_id")
        membership = get_object_or_404(Membership, pk=membership_id) if membership_id else None
        user_id = request.POST.get("user_id")
        existing_user = membership.user if membership else User.objects.filter(pk=user_id).first() if user_id else None
        if action in {"create", "update"}:
            try:
                with transaction.atomic():
                    student = build_student_from_post(request, existing_user=existing_user)
                    team_id = request.POST.get("team")
                    if team_id:
                        team = get_object_or_404(Team, pk=team_id)
                        if membership is None:
                            membership, created = Membership.objects.get_or_create(user=student, team=team)
                        else:
                            membership.user = student
                            membership.team = team
                        membership.is_active = request.POST.get("is_active") == "on"
                        membership.save()
                        messages.success(request, "Student saved and assigned successfully.")
                    else:
                        messages.success(request, "Student saved. Team can be assigned later.")
            except ValueError as exc:
                messages.error(request, str(exc))
        elif action == "deactivate" and membership:
            membership.is_active = False
            membership.save(update_fields=["is_active", "updated_at"])
            messages.success(request, "Member deactivated for this team.")
        elif action == "deactivate" and existing_user:
            existing_user.is_active = False
            existing_user.save(update_fields=["is_active"])
            messages.success(request, "Student deactivated.")
        elif action == "activate" and membership:
            membership.is_active = True
            membership.save(update_fields=["is_active", "updated_at"])
            messages.success(request, "Member activated for this team.")
        elif action == "activate" and existing_user:
            existing_user.is_active = True
            existing_user.save(update_fields=["is_active"])
            messages.success(request, "Student activated.")
        elif action == "delete" and membership:
            membership.delete()
            messages.success(request, "Member assignment deleted.")
        elif action == "delete" and existing_user:
            student_name = existing_user.get_full_name() or existing_user.email or existing_user.username
            existing_user.is_active = False
            existing_user.save(update_fields=["is_active"])
            messages.success(request, f"{student_name} moved to settings restore list.")
        return redirect("members")

    memberships = Membership.objects.select_related("user", "user__profile", "team", "team__sport")
    if not is_admin_user(request.user):
        memberships = memberships.filter(team__in=Team.objects.filter(Q(captain=request.user) | Q(vice_captain=request.user) | Q(coordinator=request.user)))
    assigned_user_ids = set()
    student_rows = []
    for membership in memberships:
        assigned_user_ids.add(membership.user_id)
        student_rows.append({"membership": membership, "user": membership.user, "team": membership.team, "is_active": membership.is_active})
    if is_admin_user(request.user):
        unassigned_students = User.objects.filter(profile__role=UserProfile.Role.MEMBER).exclude(pk__in=assigned_user_ids).select_related("profile").order_by("first_name", "last_name", "email")
        for student in unassigned_students:
            student_rows.append({"membership": None, "user": student, "team": None, "is_active": student.is_active})
    teams = Team.objects.filter(is_active=True).select_related("sport").order_by("sport__name", "name")
    login_requests = LoginAccessRequest.objects.exclude(status=LoginAccessRequest.Status.APPROVED).order_by("status", "-requested_at")
    return render(request, "core/members.html", {"memberships": memberships, "student_rows": student_rows, "teams": teams, "login_requests": login_requests})


@login_required
@role_required(*ADMIN_ROLES)
def member_detail(request, pk):
    student = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    memberships = Membership.objects.filter(user=student).select_related("team", "team__sport")
    records = AttendanceRecord.objects.filter(member=student).select_related("session", "session__team", "session__team__sport", "marked_by")
    breadcrumb_items = [
        {"label": "Dashboard", "url_name": "dashboard"},
        {"label": "Add Students", "url_name": "members"},
        {"label": student.get_full_name() or student.email or student.username},
    ]
    return render(request, "core/member_detail.html", {"student": student, "memberships": memberships, "records": records, "breadcrumb_items": breadcrumb_items})


@login_required
@role_required(*ADMIN_ROLES)
def trainers_list(request):
    if request.method == "POST":
        action = request.POST.get("action")
        trainer_id = request.POST.get("trainer_id")
        trainer = get_object_or_404(User, pk=trainer_id) if trainer_id else None
        if action in {"create", "update"}:
            full_name = request.POST.get("trainer_name", "").strip()
            email = request.POST.get("trainer_email", "").strip().lower()
            phone = request.POST.get("mobile_number", "").strip()
            selected_team_ids = request.POST.getlist("teams")
            if not email:
                messages.error(request, "Trainer email is required.")
                return redirect("trainers")
            if phone and not re.fullmatch(r"\d{10}", phone):
                messages.error(request, "Mobile number must be exactly 10 digits.")
                return redirect("trainers")
            trainer = trainer or User.objects.filter(email__iexact=email).first()
            if trainer is None:
                trainer = User(username=email, email=email)
                trainer.set_unusable_password()
            if full_name:
                parts = full_name.split(" ", 1)
                trainer.first_name = parts[0]
                trainer.last_name = parts[1] if len(parts) > 1 else ""
            trainer.email = email
            trainer.username = email
            trainer.save()
            profile, _ = UserProfile.objects.get_or_create(user=trainer)
            profile.role = UserProfile.Role.TRAINER
            profile.phone = phone
            profile.save(update_fields=["role", "phone", "updated_at"])
            Team.objects.filter(coordinator=trainer).exclude(pk__in=selected_team_ids).update(coordinator=None)
            Team.objects.filter(pk__in=selected_team_ids).update(coordinator=trainer)
            messages.success(request, "Trainer saved and assigned successfully.")
        elif action == "deactivate" and trainer:
            Team.objects.filter(coordinator=trainer).update(coordinator=None)
            trainer.profile.role = UserProfile.Role.MEMBER
            trainer.profile.save(update_fields=["role", "updated_at"])
            messages.success(request, "Trainer deactivated.")
        elif action == "activate" and trainer:
            trainer.profile.role = UserProfile.Role.TRAINER
            trainer.profile.save(update_fields=["role", "updated_at"])
            messages.success(request, "Trainer activated.")
        elif action == "delete" and trainer:
            trainer_name = trainer.get_full_name() or trainer.username
            Team.objects.filter(coordinator=trainer).update(coordinator=None)
            trainer.is_active = False
            trainer.save(update_fields=["is_active"])
            messages.success(request, f"{trainer_name} moved to settings restore list.")
        return redirect("trainers")

    trainers = User.objects.filter(
        Q(profile__role__in=[UserProfile.Role.TRAINER, UserProfile.Role.COORDINATOR])
        | Q(coordinated_teams__isnull=False)
    ).distinct().prefetch_related("coordinated_teams__sport").order_by("first_name", "last_name", "email")
    teams = Team.objects.filter(is_active=True).select_related("sport").order_by("sport__name", "gender", "name")
    return render(request, "core/trainers.html", {"trainers": trainers, "teams": teams})


@login_required
@role_required(*ADMIN_ROLES)
def settings_page(request):
    inactive_users = User.objects.filter(is_active=False).select_related("profile").order_by("first_name", "last_name", "email")
    return render(request, "core/settings.html", {"inactive_users": inactive_users})


@login_required
@role_required(*ADMIN_ROLES)
def restore_user(request, pk):
    user = get_object_or_404(User, pk=pk, is_active=False)
    user.is_active = True
    user.save(update_fields=["is_active"])
    messages.success(request, f"{user.get_full_name() or user.email or user.username} restored.")
    return redirect("settings")


@login_required
def my_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=profile, user_instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("my_profile")
    return render(request, "core/my_profile.html", {"form": form})


@login_required
@role_required(*ADMIN_ROLES)
def membership_form(request, pk=None):
    membership = get_object_or_404(Membership, pk=pk) if pk else None
    form = MembershipForm(request.POST or None, instance=membership)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Member assignment saved.")
        return redirect("members")
    return render(request, "core/form.html", {"form": form, "title": "Team Member", "back_url": reverse("members")})


@login_required
def sessions_list(request):
    if request.method == "POST":
        action = request.POST.get("action")
        session_id = request.POST.get("session_id")
        session = get_object_or_404(Session, pk=session_id) if session_id else None
        if session and action != "create" and not can_manage_team(request.user, session.team):
            messages.error(request, "You cannot manage this session.")
            return redirect("sessions")
        if action in {"create", "update"}:
            form = SessionForm(request.POST, instance=session)
            if not is_admin_user(request.user):
                form.fields["team"].queryset = Team.objects.filter(coordinator=request.user)
            if form.is_valid():
                obj = form.save(commit=False)
                if can_schedule_session(request.user, obj.team):
                    obj.scheduled_by = obj.scheduled_by or request.user
                    obj.save()
                    messages.success(request, "Practice session saved successfully.")
                else:
                    messages.error(request, "You cannot schedule for this team.")
            else:
                messages.error(request, "Please correct the session details and try again.")
        elif action == "delete" and session:
            session.delete()
            messages.success(request, "Practice session deleted.")
        return redirect("sessions")

    form = ReportFilterForm(request.GET or None)
    sessions = visible_sessions(request.user)
    if form.is_valid():
        sport = form.cleaned_data.get("sport")
        team = form.cleaned_data.get("team")
        start = form.cleaned_data.get("start_date")
        end = form.cleaned_data.get("end_date")
        if sport:
            sessions = sessions.filter(team__sport=sport)
        if team:
            sessions = sessions.filter(team=team)
        if start:
            sessions = sessions.filter(start_at__date__gte=start)
        if end:
            sessions = sessions.filter(start_at__date__lte=end)
    team_qs = Team.objects.filter(is_active=True).select_related("sport").order_by("sport__name", "name")
    if not is_admin_user(request.user):
        team_qs = team_qs.filter(coordinator=request.user)
    can_schedule_any = is_admin_user(request.user) or (role_for(request.user) in TRAINER_ROLES and team_qs.exists())
    venues = Venue.objects.filter(is_active=True).order_by("name")
    return render(request, "core/sessions.html", {"sessions": sessions, "form": form, "teams": team_qs, "venues": venues, "can_schedule_any": can_schedule_any})


@login_required
def session_form(request, pk=None):
    session = get_object_or_404(Session, pk=pk) if pk else None
    if session and not can_manage_team(request.user, session.team):
        messages.error(request, "You cannot edit this session.")
        return redirect("sessions")
    form = SessionForm(request.POST or None, instance=session)
    if not is_admin_user(request.user):
        form.fields["team"].queryset = Team.objects.filter(coordinator=request.user)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if not can_schedule_session(request.user, obj.team):
            messages.error(request, "You cannot schedule for this team.")
            return redirect("sessions")
        obj.scheduled_by = obj.scheduled_by or request.user
        obj.save()
        messages.success(request, "Practice session saved.")
        return redirect("sessions")
    return render(request, "core/form.html", {"form": form, "title": "Practice Session", "back_url": reverse("sessions")})


@login_required
def delegate_attendance(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if not can_manage_team(request.user, session.team):
        messages.error(request, "You cannot delegate attendance for this session.")
        return redirect("sessions")
    form = DelegateForm(request.POST or None, session=session)
    if request.method == "POST" and form.is_valid():
        AttendanceDelegate.objects.get_or_create(
            session=session,
            assigned_to=form.cleaned_data["assigned_to"],
            defaults={"assigned_by": request.user, "reason": form.cleaned_data["reason"]},
        )
        messages.success(request, "Attendance delegate assigned.")
        return redirect("sessions")
    return render(request, "core/form.html", {"form": form, "title": "Assign Session Incharge", "back_url": reverse("sessions")})


@login_required
def take_attendance(request, pk):
    session = get_object_or_404(Session.objects.select_related("team"), pk=pk)
    if not can_take_attendance(request.user, session):
        messages.error(request, "You cannot take attendance for this session.")
        return redirect("sessions")
    if session.attendance_submitted:
        messages.warning(request, "Attendance has already been submitted for this session.")
        return redirect("attendance_detail", pk=session.pk)
    now = timezone.now()
    with transaction.atomic():
        locked_session = Session.objects.select_for_update().get(pk=session.pk)
        lock_active = (
            locked_session.attendance_started_by
            and locked_session.attendance_started_by != request.user
            and locked_session.attendance_lock_expires_at
            and locked_session.attendance_lock_expires_at > now
        )
        if lock_active:
            messages.warning(
                request,
                f"Attendance is already being taken by {locked_session.attendance_started_by.get_full_name() or locked_session.attendance_started_by.username} ({locked_session.attendance_started_by_role}).",
            )
            return redirect("sessions")
        if not locked_session.attendance_started_by or locked_session.attendance_lock_expires_at is None or locked_session.attendance_lock_expires_at <= now:
            locked_session.attendance_started_by = request.user
            locked_session.attendance_started_by_role = role_label(request.user)
            locked_session.attendance_started_at = now
        locked_session.attendance_lock_expires_at = now + timedelta(minutes=30)
        locked_session.save(update_fields=["attendance_started_by", "attendance_started_by_role", "attendance_started_at", "attendance_lock_expires_at", "updated_at"])
        session = locked_session
    members = User.objects.filter(memberships__team=session.team, memberships__is_active=True).distinct().order_by("first_name", "last_name", "username")
    if request.method == "POST":
        with transaction.atomic():
            locked_session = Session.objects.select_for_update().get(pk=session.pk)
            if locked_session.attendance_started_by and locked_session.attendance_started_by != request.user:
                messages.warning(request, "Another authorized user is currently taking this attendance.")
                return redirect("sessions")
            for member in members:
                status = request.POST.get(f"status_{member.pk}", AttendanceRecord.Status.ABSENT)
                remarks = request.POST.get(f"remarks_{member.pk}", "")
                AttendanceRecord.objects.create(session=session, member=member, status=status, remarks=remarks, marked_by=request.user)
            locked_session.attendance_submitted = True
            locked_session.submitted_by = request.user
            locked_session.submitted_by_role = role_label(request.user)
            locked_session.submitted_at = timezone.now()
            locked_session.attendance_lock_expires_at = None
            locked_session.save(update_fields=["attendance_submitted", "submitted_by", "submitted_by_role", "submitted_at", "attendance_lock_expires_at", "updated_at"])
        messages.success(request, "Attendance submitted.")
        return redirect("attendance_detail", pk=session.pk)
    return render(request, "core/take_attendance.html", {"session": session, "members": members, "statuses": AttendanceRecord.Status.choices})


@login_required
def attendance_detail(request, pk):
    session = get_object_or_404(visible_sessions(request.user), pk=pk)
    records = session.attendance_records.select_related("member", "marked_by")
    return render(request, "core/attendance_detail.html", {"session": session, "records": records})


@login_required
@role_required(*ADMIN_ROLES)
def edit_attendance(request, pk):
    record = get_object_or_404(AttendanceRecord, pk=pk)
    old_status = record.status
    form = AttendanceEditForm(request.POST or None, instance=record)
    if request.method == "POST" and form.is_valid():
        updated = form.save()
        if old_status != updated.status:
            AttendanceEditLog.objects.create(
                attendance_record=updated,
                edited_by=request.user,
                old_status=old_status,
                new_status=updated.status,
                reason=form.cleaned_data["reason"],
            )
        messages.success(request, "Attendance updated with audit history.")
        return redirect("attendance_detail", pk=record.session.pk)
    return render(request, "core/form.html", {"form": form, "title": "Edit Attendance", "back_url": reverse("attendance_detail", args=[record.session.pk])})


@login_required
def my_attendance(request):
    records = AttendanceRecord.objects.filter(member=request.user).select_related("session", "session__team", "session__team__sport")
    return render(request, "core/my_attendance.html", {"records": records, "percentage": attendance_percentage(request.user)})


@login_required
def feedback_list(request):
    received = Feedback.objects.filter(receiver=request.user).select_related("sender", "session")
    sent = Feedback.objects.filter(sender=request.user).select_related("receiver", "session")
    received.update(is_read=True)
    return render(request, "core/feedback.html", {"received": received, "sent": sent})


@login_required
def send_feedback(request):
    if is_admin_user(request.user) or role_for(request.user) == UserProfile.Role.COORDINATOR:
        form = FeedbackForm(request.POST or None)
        feedback_type = Feedback.FeedbackType.ADMIN_TO_STUDENT if is_admin_user(request.user) else Feedback.FeedbackType.COORDINATOR_TO_STUDENT
    else:
        form = SessionFeedbackForm(request.POST or None)
        feedback_type = Feedback.FeedbackType.STUDENT_TO_ADMIN
    if request.method == "POST" and form.is_valid():
        feedback = form.save(commit=False)
        feedback.sender = request.user
        feedback.feedback_type = feedback_type
        if feedback_type == Feedback.FeedbackType.STUDENT_TO_ADMIN:
            feedback.receiver = User.objects.filter(Q(profile__role__in=ADMIN_ROLES) | Q(is_superuser=True)).first()
        if not feedback.receiver:
            messages.error(request, "No receiver is available for this feedback.")
            return redirect("feedback")
        feedback.save()
        messages.success(request, "Feedback sent privately.")
        return redirect("feedback")
    return render(request, "core/form.html", {"form": form, "title": "Feedback", "back_url": reverse("feedback")})


@login_required
@role_required(*ADMIN_ROLES)
def reports(request, export_type=None):
    form = ReportFilterForm(request.GET or None)
    records = AttendanceRecord.objects.select_related("member", "session", "session__team", "session__team__sport")
    if form.is_valid():
        sport = form.cleaned_data.get("sport")
        team = form.cleaned_data.get("team")
        student = form.cleaned_data.get("student")
        start = form.cleaned_data.get("start_date")
        end = form.cleaned_data.get("end_date")
        if sport:
            records = records.filter(session__team__sport=sport)
        if team:
            records = records.filter(session__team=team)
        if student:
            records = records.filter(member=student)
        if start:
            records = records.filter(session__start_at__date__gte=start)
        if end:
            records = records.filter(session__start_at__date__lte=end)
    records = records.order_by("-session__start_at")
    if export_type == "excel":
        return export_excel(records)
    if export_type == "pdf":
        return export_pdf(records)
    return render(request, "core/reports.html", {"form": form, "records": records[:300]})


def export_excel(records):
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance"
    ws.append(["Date", "Sport", "Team", "Gender", "Student", "Email", "Status", "Marked By", "Marked At"])
    for record in records:
        ws.append([
            record.session.start_at.strftime("%Y-%m-%d"),
            record.session.team.sport.name,
            record.session.team.name,
            record.session.team.get_gender_display(),
            record.member.get_full_name() or record.member.username,
            record.member.email,
            record.get_status_display(),
            record.marked_by.get_full_name() if record.marked_by else "",
            record.marked_at.strftime("%Y-%m-%d %H:%M"),
        ])
    output = BytesIO()
    wb.save(output)
    response = HttpResponse(output.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="attendance-report.xlsx"'
    return response


def export_pdf(records):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "Sports Attendance Report")
    y -= 30
    pdf.setFont("Helvetica", 8)
    for record in records[:500]:
        line = f"{record.session.start_at:%Y-%m-%d} | {record.session.team.sport.name} | {record.session.team.get_gender_display()} {record.session.team.name} | {record.member.get_full_name() or record.member.username} | {record.get_status_display()}"
        pdf.drawString(40, y, line[:120])
        y -= 14
        if y < 40:
            pdf.showPage()
            pdf.setFont("Helvetica", 8)
            y = height - 40
    pdf.save()
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="attendance-report.pdf"'
    return response
