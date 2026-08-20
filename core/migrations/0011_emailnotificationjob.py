from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("core", "0010_meeting")]

    operations = [
        migrations.CreateModel(
            name="EmailNotificationJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("notification_type", models.CharField(max_length=80)),
                ("context", models.JSONField(default=dict)),
                ("recipient_user_ids", models.JSONField(default=list)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("PROCESSING", "Processing"), ("SENT", "Sent"), ("FAILED", "Failed")], db_index=True, default="PENDING", max_length=12)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("next_attempt_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("last_error", models.TextField(blank=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]
