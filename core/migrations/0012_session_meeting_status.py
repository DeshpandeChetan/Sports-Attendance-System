from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_emailnotificationjob"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="status",
            field=models.CharField(
                choices=[("SCHEDULED", "Scheduled"), ("CANCELLED", "Cancelled")],
                default="SCHEDULED",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="meeting",
            name="status",
            field=models.CharField(
                choices=[("SCHEDULED", "Scheduled"), ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled")],
                default="SCHEDULED",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="meeting",
            name="ending_note",
            field=models.TextField(blank=True),
        ),
    ]
