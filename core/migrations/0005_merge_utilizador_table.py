from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_alter_utilizador_table"),
        ("core", "0004_rename_utilizador_table"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="utilizador",
            table="core_utilizador",
        ),
    ]
