# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='evaluation',
            name='only_labeled_tasks',
            field=models.BooleanField(default=True, help_text='If True, only evaluate tasks with human labels. If False, evaluate all tasks.'),
        ),
    ]
