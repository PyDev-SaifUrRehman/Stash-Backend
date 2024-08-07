# Generated by Django 5.0.3 on 2024-07-02 11:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('StashAdmin', '0001_initial'),
        ('StashClient', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='node',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trx_node', to='StashAdmin.nodesetup'),
        ),
        migrations.AddField(
            model_name='referral',
            name='commission_transactions',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='referral_trx', to='StashClient.transaction'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='sender',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='StashClient.clientuser'),
        ),
        migrations.AddField(
            model_name='referral',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referral', to='StashClient.clientuser'),
        ),
        migrations.AddField(
            model_name='clientuser',
            name='node',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='client_node', to='StashAdmin.nodesetup'),
        ),
        migrations.AddField(
            model_name='clientuser',
            name='referred_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='referred_user', to='StashClient.referral'),
        ),
    ]
