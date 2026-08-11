from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook

from .models import AttendanceRecord, Membership, Session, Sport, Team, UserProfile
from .views import import_students_from_file


User = get_user_model()


class TrainerStudentPermissionTests(TestCase):
    def setUp(self):
        self.trainer = self.make_user("trainer@christuniversity.in", UserProfile.Role.TRAINER)
        self.other_trainer = self.make_user("other-trainer@christuniversity.in", UserProfile.Role.TRAINER)
        self.assigned_student = self.make_user("assigned@christuniversity.in", UserProfile.Role.MEMBER)
        self.other_student = self.make_user("other@christuniversity.in", UserProfile.Role.MEMBER)
        self.sport = Sport.objects.create(name="Cricket")
        self.other_sport = Sport.objects.create(name="Football")
        self.assigned_team = Team.objects.create(
            sport=self.sport,
            name="University Team",
            team_type=Team.TeamType.UNIVERSITY,
            gender=Team.TeamGender.MALE,
            coordinator=self.trainer,
        )
        self.other_team = Team.objects.create(
            sport=self.other_sport,
            name="Reserve Team",
            team_type=Team.TeamType.RESERVE,
            gender=Team.TeamGender.FEMALE,
            coordinator=self.other_trainer,
        )
        self.assigned_membership = Membership.objects.create(user=self.assigned_student, team=self.assigned_team)
        self.other_membership = Membership.objects.create(user=self.other_student, team=self.other_team)

    def make_user(self, email, role):
        user = User.objects.create_user(username=email, email=email, password="pass")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save(update_fields=["role", "updated_at"])
        return user

    def test_trainer_sees_only_students_from_assigned_teams(self):
        self.client.force_login(self.trainer)

        response = self.client.get(reverse("members"))

        self.assertContains(response, self.assigned_student.email)
        self.assertNotContains(response, self.other_student.email)

    def test_trainer_can_add_student_only_to_assigned_team(self):
        self.client.force_login(self.trainer)

        response = self.client.post(reverse("members"), {
            "action": "create",
            "student_name": "New Player",
            "student_email": "new.player@christuniversity.in",
            "gender": "Female",
            "sport": self.assigned_team.sport_id,
            "team_type": self.assigned_team.team_type,
            "team": self.assigned_team.pk,
            "is_active": "on",
        })

        self.assertRedirects(response, reverse("members"))
        self.assertTrue(Membership.objects.filter(user__email="new.player@christuniversity.in", team=self.assigned_team).exists())
        self.assertEqual(User.objects.get(email="new.player@christuniversity.in").profile.gender, "Female")

    def test_trainer_cannot_add_student_to_other_team(self):
        self.client.force_login(self.trainer)

        response = self.client.post(reverse("members"), {
            "action": "create",
            "student_name": "Blocked Player",
            "student_email": "blocked.player@christuniversity.in",
            "team": self.other_team.pk,
            "is_active": "on",
        })

        self.assertRedirects(response, reverse("members"))
        self.assertFalse(Membership.objects.filter(user__email="blocked.player@christuniversity.in", team=self.other_team).exists())

    def test_trainer_can_deactivate_and_delete_assigned_membership(self):
        self.client.force_login(self.trainer)

        self.client.post(reverse("members"), {
            "action": "deactivate",
            "membership_id": self.assigned_membership.pk,
        })
        self.assigned_membership.refresh_from_db()
        self.assertFalse(self.assigned_membership.is_active)

        self.client.post(reverse("members"), {
            "action": "delete",
            "membership_id": self.assigned_membership.pk,
        })
        self.assertFalse(Membership.objects.filter(pk=self.assigned_membership.pk).exists())

    def test_trainer_cannot_modify_other_team_membership(self):
        self.client.force_login(self.trainer)

        response = self.client.post(reverse("members"), {
            "action": "deactivate",
            "membership_id": self.other_membership.pk,
        })

        self.assertRedirects(response, reverse("members"))
        self.other_membership.refresh_from_db()
        self.assertTrue(self.other_membership.is_active)

    def test_trainer_student_detail_is_restricted_to_assigned_team_records(self):
        session = Session.objects.create(
            team=self.assigned_team,
            title="Practice session",
            start_at=timezone.now(),
            end_at=timezone.now(),
            venue="Ground A",
            scheduled_by=self.trainer,
        )
        other_session = Session.objects.create(
            team=self.other_team,
            title="Other practice",
            start_at=timezone.now(),
            end_at=timezone.now(),
            venue="Ground B",
            scheduled_by=self.other_trainer,
        )
        AttendanceRecord.objects.create(session=session, member=self.assigned_student, status=AttendanceRecord.Status.PRESENT, marked_by=self.trainer)
        AttendanceRecord.objects.create(session=other_session, member=self.assigned_student, status=AttendanceRecord.Status.ABSENT, marked_by=self.other_trainer)
        Membership.objects.create(user=self.assigned_student, team=self.other_team)
        self.client.force_login(self.trainer)

        response = self.client.get(reverse("member_detail", args=[self.assigned_student.pk]))

        self.assertContains(response, "Practice session")
        self.assertContains(response, "100.0%")
        self.assertNotContains(response, "Other practice")

    def test_trainer_can_submit_attendance_for_assigned_team_session(self):
        session = Session.objects.create(
            team=self.assigned_team,
            title="Attendance Practice",
            start_at=timezone.now(),
            end_at=timezone.now(),
            venue="Ground A",
            scheduled_by=self.trainer,
        )
        self.client.force_login(self.trainer)

        response = self.client.post(reverse("take_attendance", args=[session.pk]), {
            f"status_{self.assigned_student.pk}": AttendanceRecord.Status.PRESENT,
            f"remarks_{self.assigned_student.pk}": "On time",
        })

        self.assertRedirects(response, reverse("attendance_detail", args=[session.pk]))
        session.refresh_from_db()
        self.assertTrue(session.attendance_submitted)
        self.assertEqual(session.submitted_by, self.trainer)
        record = AttendanceRecord.objects.get(session=session, member=self.assigned_student)
        self.assertEqual(record.status, AttendanceRecord.Status.PRESENT)
        self.assertEqual(record.remarks, "On time")
        self.assertEqual(record.session.team, self.assigned_team)
        self.assertEqual(record.session.team.sport, self.sport)

    def test_student_bulk_upload_supports_gender_sport_and_team_type(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Student Name", "Student Email", "Mobile Number", "Reg No", "Department", "Class", "Gender", "Sport", "Team Type", "Team", "Status"])
        sheet.append(["Bulk Player", "bulk.player@christuniversity.in", "9876543210", "B001", "MSDS", "I MSc", "Male", "Cricket", "University", "University Team", "Active"])
        uploaded = BytesIO()
        workbook.save(uploaded)
        uploaded.seek(0)

        created, errors = import_students_from_file(uploaded, self.trainer)

        self.assertEqual(created, 1)
        self.assertEqual(errors, [])
        student = User.objects.get(email="bulk.player@christuniversity.in")
        self.assertEqual(student.profile.gender, "Male")
        self.assertTrue(Membership.objects.filter(user=student, team=self.assigned_team, is_active=True).exists())
