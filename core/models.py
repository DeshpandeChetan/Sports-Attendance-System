from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserProfile(TimeStampedModel):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        SUB_ADMIN = "SUB_ADMIN", "Coordinator"
        TRAINER = "TRAINER", "Trainer"
        CAPTAIN = "CAPTAIN", "Captain"
        VICE_CAPTAIN = "VICE_CAPTAIN", "Vice Captain"
        COORDINATOR = "COORDINATOR", "Coordinator"
        MEMBER = "MEMBER", "Member"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    department = models.CharField(max_length=120, blank=True)
    class_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class LoginAccessRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="login_requests_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.email} - {self.get_status_display()}"


class Sport(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Team(TimeStampedModel):
    class TeamType(models.TextChoices):
        UNIVERSITY = "UNIVERSITY", "University"
        RESERVE = "RESERVE", "Reserve"
        RECREATIONAL = "RECREATIONAL", "Recreational"

    class TeamGender(models.TextChoices):
        BOYS = "BOYS", "Boys"
        GIRLS = "GIRLS", "Girls"

    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=120)
    team_type = models.CharField(max_length=20, choices=TeamType.choices)
    gender = models.CharField(max_length=10, choices=TeamGender.choices, default=TeamGender.BOYS)
    captain = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="captained_teams")
    vice_captain = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="vice_captained_teams")
    coordinator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinated_teams")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("sport", "name", "team_type", "gender")

    def __str__(self):
        return f"{self.sport} - {self.get_gender_display()} {self.name}"


class Membership(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    jersey_number = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    joined_on = models.DateField(default=timezone.localdate)

    class Meta:
        unique_together = ("user", "team")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.team}"


class Session(TimeStampedModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="sessions")
    title = models.CharField(max_length=160)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    venue = models.CharField(max_length=160)
    notes = models.TextField(blank=True)
    scheduled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="scheduled_sessions")
    attendance_submitted = models.BooleanField(default=False)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="submitted_sessions")
    submitted_by_role = models.CharField(max_length=40, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    attendance_started_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_sessions_started")
    attendance_started_by_role = models.CharField(max_length=40, blank=True)
    attendance_started_at = models.DateTimeField(null=True, blank=True)
    attendance_lock_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_at"]

    def __str__(self):
        return f"{self.title} - {self.team} ({self.start_at:%d %b %Y})"


class AttendanceDelegate(TimeStampedModel):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="delegates")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="delegations_made")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="delegations_received")
    assigned_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("session", "assigned_to")

    def __str__(self):
        return f"{self.assigned_to} delegated for {self.session}"


class AttendanceRecord(TimeStampedModel):
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        LATE = "LATE", "Late"
        EARLY_EXIT = "EARLY_EXIT", "Early Exit"

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="attendance_records")
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_records")
    status = models.CharField(max_length=20, choices=Status.choices)
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="attendance_marked")
    marked_at = models.DateTimeField(auto_now_add=True)
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("session", "member")
        ordering = ["member__first_name", "member__last_name", "member__username"]

    def __str__(self):
        return f"{self.member} - {self.session}: {self.status}"


class AttendanceEditLog(TimeStampedModel):
    attendance_record = models.ForeignKey(AttendanceRecord, on_delete=models.CASCADE, related_name="edit_logs")
    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    old_status = models.CharField(max_length=20, choices=AttendanceRecord.Status.choices)
    new_status = models.CharField(max_length=20, choices=AttendanceRecord.Status.choices)
    reason = models.CharField(max_length=255)
    edited_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.attendance_record} {self.old_status}->{self.new_status}"


class Feedback(TimeStampedModel):
    class FeedbackType(models.TextChoices):
        ADMIN_TO_STUDENT = "ADMIN_TO_STUDENT", "Admin to Student"
        STUDENT_TO_ADMIN = "STUDENT_TO_ADMIN", "Student to Admin"
        COORDINATOR_TO_STUDENT = "COORDINATOR_TO_STUDENT", "Coordinator to Student"

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="feedback_sent")
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedback_received")
    session = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True, blank=True, related_name="feedback")
    feedback_type = models.CharField(max_length=30, choices=FeedbackType.choices)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(message=""),
                name="feedback_message_not_empty",
            )
        ]

    def __str__(self):
        return f"{self.get_feedback_type_display()} from {self.sender} to {self.receiver}"
