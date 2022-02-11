from django.conf import settings

from dateutil.parser import parse as date_parse
from stellar_sdk import Asset as StellarAsset

from aqua_marketkeys_tracker.marketkeys.exceptions import MarketKeyParsingError
from aqua_marketkeys_tracker.marketkeys.models import MarketKey, Asset
from aqua_marketkeys_tracker.utils.stellar.asset import get_asset_string


# Deprecated
def verify_signers(account_info: dict, marker: str):
    signers = account_info['signers']
    thresholds = account_info['thresholds']
    if len(signers) != 2:
        raise MarketKeyParsingError('Invalid signers count.')

    if not any(s['key'] == marker for s in signers):
        raise MarketKeyParsingError('Market key not found.')

    if not all(s['weight'] == settings.MARKET_KEY_SIGNER_WEIGHT for s in signers):
        raise MarketKeyParsingError('Invalid signer weight.')

    if not (thresholds['low_threshold'] == thresholds['med_threshold']
            == thresholds['high_threshold'] == settings.MARKET_KEY_THRESHOLD):
        raise MarketKeyParsingError('Invalid thresholds.')


# Deprecated
def parse_market_assets(account_info: dict) -> (StellarAsset, StellarAsset):
    balances = account_info['balances']
    if len(balances) not in (2, 3):
        raise MarketKeyParsingError('Invalid assets count.')

    assets = [
        StellarAsset(b['asset_code'], b['asset_issuer'])
        for b in balances
        if b['asset_type'] != 'native'
    ]

    if len(assets) == 1:
        assets.insert(0, StellarAsset.native())

    asset1, asset2 = assets
    return asset1, asset2


# Deprecated
def parse_account_info(account_info: dict, marker: str) -> MarketKey:
    verify_signers(account_info, marker)

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


class MarketKeyParser:
    MARKET_KEY_SIGNER_WEIGHT = settings.MARKET_KEY_SIGNER_WEIGHT
    MARKET_KEY_THRESHOLD = settings.MARKET_KEY_THRESHOLD

    def __init__(self, marker_key: str, market_type: str):
        self.marker_key = marker_key
        self.market_key = market_type

        self.assets_cache = {}

    def get_asset_object(self, asset: StellarAsset) -> Asset:
        asset_string = get_asset_string(asset)

        if asset_string in self.assets_cache:
            return self.assets_cache[asset_string]

        code = asset.code
        issuer = asset.issuer or ''
        # TODO: Refactor to bulk create if needed.
        self.assets_cache[asset_string] = Asset.objects.get_or_create(code=code, issuer=issuer)[0]

        return self.assets_cache[asset_string]

    def verify_signers(self, account_info: dict):
        signers = account_info['signers']
        thresholds = account_info['thresholds']
        if len(signers) != 2:
            raise MarketKeyParsingError('Invalid signers count.')

        if not any(s['key'] == self.marker_key for s in signers):
            raise MarketKeyParsingError('Market key not found.')

        if not all(s['weight'] == self.MARKET_KEY_SIGNER_WEIGHT for s in signers):
            raise MarketKeyParsingError('Invalid signer weight.')

        if not (thresholds['low_threshold'] == thresholds['med_threshold']
                == thresholds['high_threshold'] == self.MARKET_KEY_THRESHOLD):
            raise MarketKeyParsingError('Invalid thresholds.')

    def parse_market_assets(self, account_info: dict) -> (StellarAsset, StellarAsset):
        balances = account_info['balances']
        if len(balances) not in (2, 3):
            raise MarketKeyParsingError('Invalid assets count.')

        assets = [
            StellarAsset(b['asset_code'], b['asset_issuer'])
            for b in balances
            if b['asset_type'] != 'native'
        ]

        if len(assets) == 1:
            assets.insert(0, StellarAsset.native())

        asset1, asset2 = assets
        return asset1, asset2

    def parse_account_info(self, account_info: dict) -> MarketKey:
        self.verify_signers(account_info)

        account_id = account_info['account_id']
        last_modified_time = account_info['last_modified_time']
        asset1, asset2 = self.parse_market_assets(account_info)

        asset1 = self.get_asset_object(asset1)
        asset2 = self.get_asset_object(asset2)

        return MarketKey(
            account_id=account_id,
            asset1=asset1,
            asset2=asset2,
            asset1_code=asset1.code,
            asset1_issuer=asset1.issuer,
            asset2_code=asset2.code,
            asset2_issuer=asset2.issuer,
            locked_at=date_parse(last_modified_time),
        )
