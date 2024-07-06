# Generated by Django 5.0.3 on 2024-07-05 13:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('StashClient', '0009_clientuser_maturity'),
    ]

    operations = [
        migrations.AddField(
            model_name='clientuser',
            name='total_deposit',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='transaction_type',
            field=models.CharField(choices=[('Reward Claim', 'Reward Claim'), ('SuperNode Boost', 'SuperNode Boost'), ('Generated SubNode', 'Generated SubNode'), ('Stake & Swim Boost', 'Stake & Swim Boost'), ('ETH 2.0 Node', 'ETH 2.0 Node'), ('Commission', 'Commission')], max_length=255),
        ),
    ]
