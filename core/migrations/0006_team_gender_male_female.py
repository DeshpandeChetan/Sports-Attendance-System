from django.db import migrations, models


def forwards(apps, schema_editor):
    Team = apps.get_model("core", "Team")
    Team.objects.filter(gender="BOYS").update(gender="MALE")
    Team.objects.filter(gender="GIRLS").update(gender="FEMALE")


def backwards(apps, schema_editor):
    Team = apps.get_model("core", "Team")
    Team.objects.filter(gender="MALE").update(gender="BOYS")
    Team.objects.filter(gender="FEMALE").update(gender="GIRLS")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_alter_team_gender"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="team",
            name="gender",
            field=models.CharField(
                choices=[("MALE", "Male"), ("FEMALE", "Female")],
                default="MALE",
                max_length=10,
            ),
        ),
    ]
