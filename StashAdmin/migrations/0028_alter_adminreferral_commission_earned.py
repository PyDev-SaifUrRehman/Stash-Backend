# Generated by Django 5.1.2 on 2024-10-16 07:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('StashAdmin', '0027_delete_adminuser'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adminreferral',
            name='commission_earned',
            field=models.DecimalField(decimal_places=6, default=0, max_digits=14),
        ),
    ]
