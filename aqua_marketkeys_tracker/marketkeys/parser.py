from django.conf import settings

from dateutil.parser import parse as date_parse
from stellar_sdk import Asset as StellarAsset
from stellar_sdk import StrKey

from aqua_marketkeys_tracker.marketkeys.exceptions import MarketKeyParsingError
from aqua_marketkeys_tracker.marketkeys.models import Asset, MarketKey
from aqua_marketkeys_tracker.utils.stellar.asset import get_asset_string
from aqua_marketkeys_tracker.utils.stellar.soroban import ContractDecodeError, decode_data_entry_contract

TOKEN_DATA_ENTRY_KEYS = ('token_1', 'token_2')


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

    asset1 = Asset(code=asset1.code, issuer=asset1.issuer or '')
    asset2 = Asset(code=asset2.code, issuer=asset2.issuer or '')

    return MarketKey(
        account_id=account_id,
        asset1=asset1,
        asset2=asset2,
        locked_at=date_parse(last_modified_time) if last_modified_time else None,
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
        contract_id = asset.contract_id(settings.STELLAR_PASSPHRASE)
        # TODO: Refactor to bulk create if needed.
        asset_object, created = Asset.objects.get_or_create(
            code=code,
            issuer=issuer,
            is_sac=True,
            defaults={'contract_id': contract_id},
        )
        if not asset_object.contract_id:
            asset_object.contract_id = contract_id
            asset_object.save(update_fields=['contract_id'])

        self.assets_cache[asset_string] = asset_object

        return self.assets_cache[asset_string]

    def get_contract_asset_object(self, contract_id: str) -> Asset:
        if contract_id in self.assets_cache:
            return self.assets_cache[contract_id]

        asset_object = Asset.objects.filter(contract_id=contract_id).first()

        if asset_object is None:
            asset_object = Asset.objects.create(
                code='',
                issuer='',
                contract_id=contract_id,
                is_sac=False,
            )

        self.assets_cache[contract_id] = asset_object

        return self.assets_cache[contract_id]

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

    def parse_token_contracts(self, account_info: dict) -> list:
        """Extract soroban token contract ids from token_1/token_2 manageData entries."""
        data = account_info.get('data') or {}

        contract_ids = []
        for key in TOKEN_DATA_ENTRY_KEYS:
            if key not in data:
                continue
            try:
                contract_ids.append(decode_data_entry_contract(data[key]))
            except ContractDecodeError as exc:
                raise MarketKeyParsingError(str(exc))

        if len(set(contract_ids)) != len(contract_ids):
            raise MarketKeyParsingError('Duplicated token contracts in data entries.')

        return contract_ids

    def parse_market_assets(self, account_info: dict) -> (Asset, Asset):
        trustline_assets = [
            StellarAsset(b['asset_code'], b['asset_issuer'])
            for b in account_info['balances']
            if b['asset_type'] != 'native'
        ]
        token_contracts = self.parse_token_contracts(account_info)

        if len(trustline_assets) + len(token_contracts) not in (1, 2):
            raise MarketKeyParsingError('Invalid assets count.')

        assets = [self.get_asset_object(asset) for asset in trustline_assets]
        assets += [self.get_contract_asset_object(contract_id) for contract_id in token_contracts]

        # A single trustline/token means the second asset of the pair is XLM.
        if len(assets) == 1:
            assets.insert(0, self.get_asset_object(StellarAsset.native()))

        # Canonical pair order (same as AMM): sort by contract id bytes.
        assets.sort(key=lambda asset: StrKey.decode_contract(asset.contract_id))

        asset1, asset2 = assets
        if asset1.pk == asset2.pk:
            raise MarketKeyParsingError('Assets in pair must be different.')

        return asset1, asset2

    def parse_account_info(self, account_info: dict) -> MarketKey:
        self.verify_signers(account_info)

        account_id = account_info['account_id']
        last_modified_time = account_info['last_modified_time']
        asset1, asset2 = self.parse_market_assets(account_info)

        return MarketKey(
            account_id=account_id,
            asset1=asset1,
            asset2=asset2,
            locked_at=date_parse(last_modified_time) if last_modified_time else None,
        )
