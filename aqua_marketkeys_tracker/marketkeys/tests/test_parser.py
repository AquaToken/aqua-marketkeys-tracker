import base64
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase

from stellar_sdk import Asset as StellarAsset

from aqua_marketkeys_tracker.marketkeys.exceptions import MarketKeyParsingError
from aqua_marketkeys_tracker.marketkeys.models import Asset
from aqua_marketkeys_tracker.marketkeys.parser import MarketKeyParser
from aqua_marketkeys_tracker.utils.stellar.soroban import TokenResolveError


MARKER_KEY = 'GA2UB7VXXXUSEAQUAXXXAQUARIUSVOTINGWALLETXXXPOWEREDBYAQUA'
MARKET_KEY_1 = 'GCEKYT43PEYLZ3IPIF7P4HWQXXIRISY7ZVI4JAET4CMK6HQWBCZAYPWR'
MARKET_KEY_2 = 'GBBHTVGITMDOT576BDCB4MHBKUDBWMWJOYFF476KMYA5GCH6XOJC625I'

CLASSIC_CODE = 'AQUA'
CLASSIC_ISSUER = 'GAHPYWLK6YRN7CVYZOO4H3VDRZ7PVF5UJGLZCSPAEIKJE2XSWF5LAGER'

# A real pure-soroban token contract (testnet "Soroban Custom Token 18 Cheap").
SOROBAN_CONTRACT = 'CC4I7OKC2T37HAGOOBRQ3JGSWNZC32BZFWGFJMYEDUO3U3SZPPUHPEHZ'


def classic_asset() -> StellarAsset:
    return StellarAsset(CLASSIC_CODE, CLASSIC_ISSUER)


def sac_of_classic() -> str:
    return classic_asset().contract_id(settings.STELLAR_PASSPHRASE)


def account_info(account_id: str, *, balances=None, data=None) -> dict:
    """Minimal market-key account payload accepted by the parser."""
    return {
        'account_id': account_id,
        'last_modified_time': '2026-07-01T00:00:00Z',
        'signers': [
            {'key': MARKER_KEY, 'weight': settings.MARKET_KEY_SIGNER_WEIGHT},
            {'key': account_id, 'weight': settings.MARKET_KEY_SIGNER_WEIGHT},
        ],
        'thresholds': {
            'low_threshold': settings.MARKET_KEY_THRESHOLD,
            'med_threshold': settings.MARKET_KEY_THRESHOLD,
            'high_threshold': settings.MARKET_KEY_THRESHOLD,
        },
        'balances': balances if balances is not None else [{'asset_type': 'native'}],
        'data': {
            key: base64.b64encode(value.encode()).decode()
            for key, value in (data or {}).items()
        },
    }


def soroban_market(account_id: str, contract_id: str) -> dict:
    """Market key whose single token is defined by a token_1 data entry (pair with XLM)."""
    return account_info(account_id, data={'token_1': contract_id})


def classic_market(account_id: str, asset: StellarAsset) -> dict:
    """Market key whose single trustline defines the pair (pair with XLM)."""
    return account_info(
        account_id,
        balances=[
            {'asset_type': 'native'},
            {'asset_type': 'credit_alphanum4', 'asset_code': asset.code, 'asset_issuer': asset.issuer},
        ],
    )


class SacInTokenDataEntryTestCase(TestCase):
    """`token_N` may hold the SAC address of a classic asset instead of a soroban token."""

    def setUp(self):
        self.parser = MarketKeyParser(MARKER_KEY, NotImplemented)

    def test_sac_token_entry_is_stored_as_classic_asset(self):
        with patch(
            'aqua_marketkeys_tracker.marketkeys.parser.resolve_classic_asset',
            return_value=classic_asset(),
        ) as resolve_mock:
            market_key = self.parser.parse_account_info(soroban_market(MARKET_KEY_1, sac_of_classic()))

        resolve_mock.assert_called_once_with(sac_of_classic())

        asset = Asset.objects.get(contract_id=sac_of_classic())
        self.assertTrue(asset.is_sac)
        self.assertEqual(asset.code, CLASSIC_CODE)
        self.assertEqual(asset.issuer, CLASSIC_ISSUER)
        self.assertIn(asset.pk, (market_key.asset1_id, market_key.asset2_id))
        # No squatting soroban row was created for the SAC address.
        self.assertEqual(Asset.objects.filter(is_sac=False).count(), 0)

    def test_classic_market_after_sac_token_entry_reuses_the_same_asset(self):
        """Regression: soroban market key on SAC(X) first, classic market key on X second.

        The classic path used to `get_or_create` on `(code, issuer, is_sac=True)`,
        which violated `uniq_asset_contract` and crashed `task_update_market_keys`
        on every beat run.
        """
        with patch(
            'aqua_marketkeys_tracker.marketkeys.parser.resolve_classic_asset',
            return_value=classic_asset(),
        ):
            self.parser.parse_account_info(soroban_market(MARKET_KEY_1, sac_of_classic()))

        # Fresh parser: no in-memory cache, exactly like the next celery beat run.
        second_parser = MarketKeyParser(MARKER_KEY, NotImplemented)
        market_key = second_parser.parse_account_info(classic_market(MARKET_KEY_2, classic_asset()))

        self.assertEqual(Asset.objects.filter(contract_id=sac_of_classic()).count(), 1)
        asset = Asset.objects.get(contract_id=sac_of_classic())
        self.assertTrue(asset.is_sac)
        self.assertIn(asset.pk, (market_key.asset1_id, market_key.asset2_id))

    def test_existing_squatted_soroban_row_is_upgraded_in_place(self):
        """Rows created before the fix shipped are adopted instead of crashing."""
        squatted = Asset.objects.create(
            code='',
            issuer='',
            contract_id=sac_of_classic(),
            is_sac=False,
            in_asset_registry=True,
        )

        self.parser.parse_account_info(classic_market(MARKET_KEY_2, classic_asset()))

        squatted.refresh_from_db()
        self.assertTrue(squatted.is_sac)
        self.assertEqual(squatted.code, CLASSIC_CODE)
        self.assertEqual(squatted.issuer, CLASSIC_ISSUER)
        # Registry state is preserved by the upgrade.
        self.assertTrue(squatted.in_asset_registry)
        self.assertEqual(Asset.objects.filter(contract_id=sac_of_classic()).count(), 1)

    def test_pure_soroban_token_is_stored_as_soroban_asset(self):
        with patch(
            'aqua_marketkeys_tracker.marketkeys.parser.resolve_classic_asset',
            return_value=None,
        ):
            self.parser.parse_account_info(soroban_market(MARKET_KEY_1, SOROBAN_CONTRACT))

        asset = Asset.objects.get(contract_id=SOROBAN_CONTRACT)
        self.assertFalse(asset.is_sac)
        self.assertEqual(asset.code, '')

    def test_unresolvable_contract_skips_the_account(self):
        """An RPC failure must not fall back to "pure soroban token"."""
        with patch(
            'aqua_marketkeys_tracker.marketkeys.parser.resolve_classic_asset',
            side_effect=TokenResolveError('rpc down'),
        ):
            with self.assertRaises(MarketKeyParsingError):
                self.parser.parse_account_info(soroban_market(MARKET_KEY_1, SOROBAN_CONTRACT))

        self.assertFalse(Asset.objects.filter(contract_id=SOROBAN_CONTRACT).exists())

    def test_known_contract_is_not_resolved_again(self):
        """The Asset row is the cache: RPC is hit once per newly seen contract."""
        Asset.objects.create(code='', issuer='', contract_id=SOROBAN_CONTRACT, is_sac=False)

        with patch('aqua_marketkeys_tracker.marketkeys.parser.resolve_classic_asset') as resolve_mock:
            self.parser.parse_account_info(soroban_market(MARKET_KEY_1, SOROBAN_CONTRACT))

        resolve_mock.assert_not_called()
