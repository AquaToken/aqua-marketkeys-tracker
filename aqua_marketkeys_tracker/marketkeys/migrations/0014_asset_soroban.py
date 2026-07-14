from django.conf import settings
from django.db import migrations, models


def backfill_contract_ids(apps, schema_editor):
    from stellar_sdk import Asset as StellarAsset

    Asset = apps.get_model('marketkeys', 'Asset')

    for asset in Asset.objects.filter(contract_id=''):
        stellar_asset = StellarAsset(asset.code, asset.issuer or None)
        asset.contract_id = stellar_asset.contract_id(settings.STELLAR_PASSPHRASE)
        asset.is_sac = True
        asset.save(update_fields=['contract_id', 'is_sac'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('marketkeys', '0013_asset_in_asset_registry'),
    ]

    operations = [
        # Cleanup of unused downvote fields.
        migrations.RemoveField(
            model_name='asset',
            name='downvote_immunity',
        ),
        migrations.RemoveField(
            model_name='marketkey',
            name='downvote_account_id',
        ),
        # Soroban tokens support.
        migrations.AlterUniqueTogether(
            name='asset',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='asset',
            name='code',
            field=models.CharField(max_length=32),
        ),
        migrations.AlterField(
            model_name='asset',
            name='issuer',
            field=models.CharField(blank=True, max_length=56),
        ),
        migrations.AddField(
            model_name='asset',
            name='contract_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=56),
        ),
        migrations.AddField(
            model_name='asset',
            name='is_sac',
            field=models.BooleanField(default=True),
        ),
        migrations.AddConstraint(
            model_name='asset',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_sac', True)),
                fields=('code', 'issuer'),
                name='uniq_classic_asset',
            ),
        ),
        migrations.AddConstraint(
            model_name='asset',
            constraint=models.UniqueConstraint(
                condition=models.Q(('contract_id', ''), _negated=True),
                fields=('contract_id',),
                name='uniq_asset_contract',
            ),
        ),
        migrations.RunPython(backfill_contract_ids, noop),
    ]
