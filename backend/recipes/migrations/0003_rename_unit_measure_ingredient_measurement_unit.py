# Generated by Django 3.2.16 on 2024-09-29 07:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0002_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ingredient',
            old_name='unit_measure',
            new_name='measurement_unit',
        ),
    ]
