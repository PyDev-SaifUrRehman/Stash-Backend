# Generated by Django 5.1.2 on 2024-10-17 12:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('StashClient', '0041_alter_transaction_setup_charges'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clientuser',
            name='admin_added_claimed_reward',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
        migrations.AlterField(
            model_name='clientuser',
            name='admin_added_deposit',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
        migrations.AlterField(
            model_name='clientuser',
            name='admin_maturity',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
        migrations.AlterField(
            model_name='clientuser',
            name='claimed_reward',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AlterField(
            model_name='clientuser',
            name='generated_reward',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AlterField(
            model_name='clientuser',
            name='maturity',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AlterField(
            model_name='clientuser',
            name='total_deposit',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AlterField(
            model_name='clientuser',
            name='total_revenue',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AlterField(
            model_name='referral',
            name='commission_earned',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='setup_charges',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
    ]
