# Generated by Django 5.0.3 on 2024-07-06 11:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('StashClient', '0011_alter_transaction_node_quantity_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='block_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
