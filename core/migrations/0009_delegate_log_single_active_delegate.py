from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def collapse_duplicate_delegates(apps, schema_editor):
    AttendanceDelegate = apps.get_model("core", "AttendanceDelegate")
    AttendanceDelegateLog = apps.get_model("core", "AttendanceDelegateLog")
    Session = apps.get_model("core", "Session")

    session_ids = (
        AttendanceDelegate.objects.values_list("session_id", flat=True)
        .distinct()
    )
    for session_id in session_ids:
        delegates = list(
            AttendanceDelegate.objects.filter(session_id=session_id).order_by("-assigned_at", "-id")
        )
        if len(delegates) <= 1:
            continue
        keep = delegates[0]
        for old_delegate in delegates[1:]:
            AttendanceDelegateLog.objects.create(
                session_id=session_id,
                previous_delegate_id=old_delegate.assigned_to_id,
                new_delegate_id=keep.assigned_to_id,
                changed_by_id=keep.assigned_by_id,
                reason="Cleaned up duplicate active delegates while enforcing one active delegate per session.",
            )
            old_delegate.delete()
        session = Session.objects.filter(pk=session_id).first()
        if session:
            AttendanceDelegateLog.objects.create(
                session_id=session_id,
                previous_delegate_id=None,
                new_delegate_id=keep.assigned_to_id,
                changed_by_id=keep.assigned_by_id,
                reason="Retained as active Session Incharge.",
            )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0008_userprofile_profile_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="AttendanceDelegateLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("changed_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="delegate_changes_made", to=settings.AUTH_USER_MODEL)),
                ("new_delegate", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="new_delegate_logs", to=settings.AUTH_USER_MODEL)),
                ("previous_delegate", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="previous_delegate_logs", to=settings.AUTH_USER_MODEL)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="delegate_logs", to="core.session")),
            ],
            options={
                "ordering": ["-changed_at"],
            },
        ),
        migrations.RunPython(collapse_duplicate_delegates, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="attendancedelegate",
            unique_together={("session",)},
        ),
    ]
