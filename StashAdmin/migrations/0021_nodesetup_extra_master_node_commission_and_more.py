# Generated by Django 5.0.3 on 2024-07-23 06:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('StashAdmin', '0020_nodepayout'),
    ]

    operations = [
        migrations.AddField(
            model_name='nodesetup',
            name='extra_master_node_commission',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=3),
        ),
        migrations.AddField(
            model_name='nodesetup',
            name='extra_master_node_reward_claim_percentage',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=3),
        ),
        migrations.AddField(
            model_name='nodesetup',
            name='extra_super_node_commission',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=3),
        ),
        migrations.AddField(
            model_name='nodesetup',
            name='extra_super_node_reward_claim_percentage',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=3),
        ),
        migrations.AddField(
            model_name='nodesetup',
            name='master_node_cost',
            field=models.PositiveIntegerField(default=20000),
        ),
        migrations.AddField(
            model_name='nodesetup',
            name='super_node_cost',
            field=models.PositiveIntegerField(default=20000),
        ),
        migrations.AlterField(
            model_name='nodesetup',
            name='node_commission_percentage',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=3),
        ),
        migrations.AlterField(
            model_name='nodesetup',
            name='reward_claim_percentage',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=3),
        ),
    ]
