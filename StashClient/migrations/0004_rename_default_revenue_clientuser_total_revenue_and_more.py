# Generated by Django 5.0.3 on 2024-07-03 12:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('StashClient', '0003_rename_trx_type_transaction_transaction_type'),
    ]

    operations = [
        migrations.RenameField(
            model_name='clientuser',
            old_name='default_revenue',
            new_name='total_revenue',
        ),
        migrations.AddField(
            model_name='transaction',
            name='setup_charges',
            field=models.DecimalField(decimal_places=2, default=100, max_digits=14),
        ),
    ]
