# Generated by Django 5.0.3 on 2024-07-04 07:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('StashClient', '0005_transaction_amount'),
    ]

    operations = [
        migrations.RenameField(
            model_name='transaction',
            old_name='mode_quantity',
            new_name='node_quantity',
        ),
    ]
