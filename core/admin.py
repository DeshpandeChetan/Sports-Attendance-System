from django.contrib import admin

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
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "department", "class_name", "phone")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")


@admin.register(LoginAccessRequest)
class LoginAccessRequestAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "status", "requested_at", "reviewed_by", "reviewed_at")
    list_filter = ("status", "requested_at")
    search_fields = ("email", "full_name")


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "sport", "team_type", "gender", "captain", "vice_captain", "coordinator", "is_active")
    list_filter = ("sport", "team_type", "gender", "is_active")
    search_fields = ("name", "sport__name")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "jersey_number", "is_active", "joined_on")
    list_filter = ("team__sport", "team__team_type", "is_active")
    search_fields = ("user__username", "user__email", "team__name")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("title", "team", "start_at", "end_at", "venue", "attendance_submitted", "scheduled_by", "attendance_started_by")
    list_filter = ("team__sport", "team__team_type", "attendance_submitted")
    search_fields = ("title", "team__name", "venue")


@admin.register(AttendanceDelegate)
class AttendanceDelegateAdmin(admin.ModelAdmin):
    list_display = ("session", "assigned_to", "assigned_by", "assigned_at")
    list_filter = ("session__team__sport",)
    search_fields = ("assigned_to__username", "assigned_to__email", "session__title")


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("session", "member", "status", "marked_by", "marked_at")
    list_filter = ("status", "session__team__sport", "session__team")
    search_fields = ("member__username", "member__email", "session__title")


@admin.register(AttendanceEditLog)
class AttendanceEditLogAdmin(admin.ModelAdmin):
    list_display = ("attendance_record", "old_status", "new_status", "edited_by", "edited_at")
    list_filter = ("old_status", "new_status")


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("feedback_type", "sender", "receiver", "session", "is_read", "created_at")
    list_filter = ("feedback_type", "is_read")
    search_fields = ("sender__username", "receiver__username", "message")
