# Generated by Django 3.2.9 on 2022-01-21 12:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketkeys', '0002_marketkey_downvote_account_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='marketkey',
            name='is_auth_required',
            field=models.BooleanField(default=False),
        ),
    ]