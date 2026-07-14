from django.conf import settings

from stellar_sdk import Asset, StrKey


def get_asset_string(asset: Asset) -> str:
    if asset.is_native():
        return 'native'

    return f'{asset.code}:{asset.issuer}'


def parse_asset_string(asset_string: str) -> Asset:
    if asset_string == 'native':
        return Asset.native()

    code, issuer = asset_string.split(':')
    return Asset(code, issuer)


def get_contract_id_for_asset_param(value: str) -> str:
    """Resolve an API asset parameter (contract id, 'native' or 'CODE:ISSUER') into a contract id."""
    if StrKey.is_valid_contract(value):
        return value

    try:
        return parse_asset_string(value).contract_id(settings.STELLAR_PASSPHRASE)
    except Exception as exc:
        raise ValueError(f'Invalid asset: {value}') from exc
