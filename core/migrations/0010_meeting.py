from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_delegate_log_single_active_delegate"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Meeting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=160)),
                ("meeting_date", models.DateField()),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("venue", models.CharField(max_length=160)),
                ("agenda", models.TextField(blank=True)),
                ("participants", models.ManyToManyField(blank=True, related_name="meetings", to=settings.AUTH_USER_MODEL)),
                ("scheduled_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="meetings_scheduled", to=settings.AUTH_USER_MODEL)),
                ("sports", models.ManyToManyField(blank=True, related_name="meetings", to="core.sport")),
                ("teams", models.ManyToManyField(blank=True, related_name="meetings", to="core.team")),
                ("trainers", models.ManyToManyField(blank=True, related_name="trainer_meetings", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-meeting_date", "-start_time"],
            },
        ),
    ]
