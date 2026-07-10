from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_page, name="login"),
    path("sports/", views.sports_list, name="sports"),
    path("sports/new/", views.sport_form, name="sport_create"),
    path("sports/<int:pk>/edit/", views.sport_form, name="sport_edit"),
    path("teams/", views.teams_list, name="teams"),
    path("teams/new/", views.team_form, name="team_create"),
    path("teams/<int:pk>/edit/", views.team_form, name="team_edit"),
    path("members/", views.members_list, name="members"),
    path("trainers/", views.trainers_list, name="trainers"),
    path("members/new/", views.membership_form, name="membership_create"),
    path("members/<int:pk>/edit/", views.membership_form, name="membership_edit"),
    path("sessions/", views.sessions_list, name="sessions"),
    path("sessions/new/", views.session_form, name="session_create"),
    path("sessions/<int:pk>/edit/", views.session_form, name="session_edit"),
    path("sessions/<int:pk>/delegate/", views.delegate_attendance, name="delegate_attendance"),
    path("sessions/<int:pk>/attendance/", views.take_attendance, name="take_attendance"),
    path("sessions/<int:pk>/attendance/detail/", views.attendance_detail, name="attendance_detail"),
    path("attendance/<int:pk>/edit/", views.edit_attendance, name="edit_attendance"),
    path("my-attendance/", views.my_attendance, name="my_attendance"),
    path("feedback/", views.feedback_list, name="feedback"),
    path("feedback/send/", views.send_feedback, name="send_feedback"),
    path("reports/", views.reports, name="reports"),
    path("reports/<str:export_type>/", views.reports, name="reports_export"),
]
