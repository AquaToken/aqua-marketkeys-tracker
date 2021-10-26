from django.conf import settings

from dateutil.parser import parse as date_parse
from stellar_sdk import Asset

from aqua_marketkeys_tracker.marketkeys.exceptions import MarketKeyParsingError
from aqua_marketkeys_tracker.marketkeys.models import MarketKey


def verify_signers(account_info):
    signers = account_info['signers']
    thresholds = account_info['thresholds']
    if len(signers) != 2:
        raise MarketKeyParsingError('Invalid signers count.')

    if not any(s['key'] == settings.MARKET_KEY_MARKER for s in signers):
        raise MarketKeyParsingError('Market key not found.')

    if not all(s['weight'] == settings.MARKET_KEY_SIGNER_WEIGHT for s in signers):
        raise MarketKeyParsingError('Invalid signer weight.')

    if not (thresholds['low_threshold'] == thresholds['med_threshold']
            == thresholds['high_threshold'] == settings.MARKET_KEY_THRESHOLD):
        raise MarketKeyParsingError('Invalid thresholds.')


def parse_market_assets(account_info: dict) -> (Asset, Asset):
    balances = account_info['balances']
    if len(balances) not in (2, 3):
        raise MarketKeyParsingError('Invalid assets count.')

    assets = [
        Asset(b['asset_code'], b['asset_issuer'])
        for b in balances
        if b['asset_type'] != 'native'
    ]

    if len(assets) == 1:
        assets.insert(0, Asset.native())

    asset1, asset2 = assets
    return asset1, asset2


def parse_account_info(account_info: dict) -> MarketKey:
    verify_signers(account_info)

    account_id = account_info['account_id']
    last_modified_time = account_info['last_modified_time']
    asset1, asset2 = parse_market_assets(account_info)

    return MarketKey(
        account_id=account_id,
        asset1_code=asset1.code,
        asset1_issuer=asset1.issuer or '',
        asset2_code=asset2.code,
        asset2_issuer=asset2.issuer or '',
        locked_at=date_parse(last_modified_time),
    )
