import re

from django.conf import settings

from dateutil.parser import parse as date_parse
from stellar_sdk import Asset as StellarAsset
from stellar_sdk import StrKey

from aqua_marketkeys_tracker.marketkeys.exceptions import MarketKeyParsingError
from aqua_marketkeys_tracker.marketkeys.models import Asset, MarketKey
from aqua_marketkeys_tracker.utils.stellar.asset import get_asset_string
from aqua_marketkeys_tracker.utils.stellar.soroban import (
    ContractDecodeError,
    TokenResolveError,
    decode_data_entry_contract,
    resolve_classic_asset,
)


TOKEN_DATA_ENTRY_KEYS = ('token_1', 'token_2')
# Matches every `token_<n>` data entry, including the ones a pair cannot have, so
# that they are rejected instead of ignored.
TOKEN_DATA_ENTRY_KEY_RE = re.compile(r'^token_\d+$')

# The only balance types a market key account may hold besides `native`. They are
# also the only ones carrying `asset_code` / `asset_issuer`.
CLASSIC_TRUSTLINE_TYPES = ('credit_alphanum4', 'credit_alphanum12')


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
        # Set when the parser creates an Asset row it has not seen before.
        # New assets have in_asset_registry=False until the registry sync runs,
        # so the caller should trigger the sync right away.
        self.created_new_assets = False

    def _cache_asset(self, asset_object: Asset, *keys: str) -> Asset:
        # An asset is reachable both by its asset string and by its contract id
        # (a classic asset and its SAC address are the same Asset row), so cache
        # it under every key it can be looked up by.
        for key in (*keys, asset_object.contract_id):
            if key:
                self.assets_cache[key] = asset_object

        return asset_object

    def get_asset_object(self, asset: StellarAsset) -> Asset:
        asset_string = get_asset_string(asset)

        if asset_string in self.assets_cache:
            return self.assets_cache[asset_string]

        code = asset.code
        issuer = asset.issuer or ''
        contract_id = asset.contract_id(settings.STELLAR_PASSPHRASE)

        # Resolve by contract id first: the SAC address is unique per asset, and a
        # row may already exist for it (e.g. created as a soroban token before this
        # asset was seen as a trustline). Creating a second row would violate
        # `uniq_asset_contract` and crash the whole market key update task.
        asset_object = Asset.objects.filter(contract_id=contract_id).first()

        if asset_object is not None:
            if not asset_object.is_sac:
                # Adopt the squatted row instead of failing: it is the same asset.
                asset_object.code = code
                asset_object.issuer = issuer
                asset_object.is_sac = True
                asset_object.save(update_fields=['code', 'issuer', 'is_sac'])
                self.created_new_assets = True

            return self._cache_asset(asset_object, asset_string)

        # TODO: Refactor to bulk create if needed.
        asset_object, created = Asset.objects.get_or_create(
            code=code,
            issuer=issuer,
            is_sac=True,
            defaults={'contract_id': contract_id},
        )
        if created:
            self.created_new_assets = True
        if not asset_object.contract_id:
            asset_object.contract_id = contract_id
            asset_object.save(update_fields=['contract_id'])

        return self._cache_asset(asset_object, asset_string)

    def get_contract_asset_object(self, contract_id: str) -> Asset:
        if contract_id in self.assets_cache:
            return self.assets_cache[contract_id]

        asset_object = Asset.objects.filter(contract_id=contract_id).first()

        if asset_object is not None:
            return self._cache_asset(asset_object)

        # A `token_N` entry may point at the SAC of a classic asset instead of a
        # pure soroban token. Such a market must be tracked as a classic pair,
        # otherwise the same market becomes trackable twice and the SAC address
        # squats the contract id of the classic asset row.
        try:
            classic_asset = resolve_classic_asset(contract_id)
        except TokenResolveError as exc:
            # Retry on the next run instead of guessing: defaulting to "pure
            # soroban token" here would create the squatting row on any RPC hiccup.
            raise MarketKeyParsingError(str(exc))

        if classic_asset is not None:
            return self.get_asset_object(classic_asset)

        asset_object = Asset.objects.create(
            code='',
            issuer='',
            contract_id=contract_id,
            is_sac=False,
        )
        self.created_new_assets = True

        return self._cache_asset(asset_object)

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

        # A pair has at most two tokens, so `token_3` and up are not "extra data" to
        # skip over — they are an attempt to declare a token that would be silently
        # dropped, leaving the account parsed as a pair it does not describe.
        # Numbering must also start at token_1: accepting a lone `token_2` would give
        # the same market two different on-chain representations.
        declared = sorted(key for key in data if TOKEN_DATA_ENTRY_KEY_RE.match(key))
        if declared != list(TOKEN_DATA_ENTRY_KEYS[:len(declared)]):
            raise MarketKeyParsingError(f'Unexpected token data entries: {declared}.')

        contract_ids = []
        for key in declared:
            try:
                contract_ids.append(decode_data_entry_contract(data[key]))
            except ContractDecodeError as exc:
                raise MarketKeyParsingError(str(exc))

        if len(set(contract_ids)) != len(contract_ids):
            raise MarketKeyParsingError('Duplicated token contracts in data entries.')

        return contract_ids

    def parse_market_assets(self, account_info: dict) -> (Asset, Asset):
        # A market key account must carry nothing besides XLM and the trustlines of
        # its own pair. Any other balance type — `liquidity_pool_shares` today,
        # whatever Horizon adds later — means this is not a well-formed market key,
        # so the account is rejected rather than parsed on a best-effort basis.
        # Selecting types explicitly also keeps `asset_code` lookups safe: pool
        # shares carry no asset code, and reading it raised an unhandled KeyError.
        trustline_assets = []
        for balance in account_info['balances']:
            asset_type = balance['asset_type']
            if asset_type == 'native':
                continue

            if asset_type not in CLASSIC_TRUSTLINE_TYPES:
                raise MarketKeyParsingError(f'Unexpected balance type: {asset_type}.')

            trustline_assets.append(StellarAsset(balance['asset_code'], balance['asset_issuer']))

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
