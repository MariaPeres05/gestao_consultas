from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_alter_utilizador_table"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="utilizador",
            table="core_utilizador",
        ),
    ]
