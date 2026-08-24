from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_session_meeting_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="account_status",
            field=models.CharField(
                choices=[("ACTIVE", "Active"), ("DEACTIVATED", "Deactivated"), ("DELETED", "Deleted")],
                default="ACTIVE",
                max_length=20,
            ),
        ),
    ]
