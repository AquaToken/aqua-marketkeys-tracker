from decimal import Decimal

from django.db import models

from stellar_sdk import Asset as StellarAsset

from aqua_marketkeys_tracker.utils.stellar.asset import get_asset_string


class AssetQuerySet(models.QuerySet):
    def get_chunk(self, cursor, chunk_size):
        return self.order_by('id').filter(id__gt=cursor)[:chunk_size]


class Asset(models.Model):
    # For classic assets `code` is the asset code, for soroban tokens it is the contract symbol().
    code = models.CharField(max_length=32)
    issuer = models.CharField(max_length=56, blank=True)

    # Contract id (C...). For classic assets it is the deterministic SAC address,
    # for pure soroban tokens it is the token contract itself.
    contract_id = models.CharField(max_length=56, blank=True, default='', db_index=True)
    # True for classic assets (contract_id points to a Stellar Asset Contract),
    # False for pure soroban tokens.
    is_sac = models.BooleanField(default=True)

    voting_boost = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    in_asset_registry = models.BooleanField(default=False)

    objects = AssetQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['code', 'issuer'],
                condition=models.Q(is_sac=True),
                name='uniq_classic_asset',
            ),
            models.UniqueConstraint(
                fields=['contract_id'],
                condition=~models.Q(contract_id=''),
                name='uniq_asset_contract',
            ),
        ]
        indexes = [
            models.Index(fields=['code', 'issuer']),
        ]

    def __str__(self):
        return self.get_asset_string()

    def get_asset_string(self) -> str:
        if not self.is_sac:
            return self.contract_id
        return get_asset_string(self.get_stellar_asset())

    def get_stellar_asset(self) -> StellarAsset:
        if not self.is_sac:
            raise ValueError('Soroban token has no classic asset representation.')
        return StellarAsset(self.code, self.issuer or None)


class MarketKeyQuerySet(models.QuerySet):
    def filter_active(self):
        return self.filter(is_active=True)

    def filter_for_contract_pair(self, contract_id1: str, contract_id2: str):
        return self.filter(
            models.Q(
                asset1__contract_id=contract_id1,
                asset2__contract_id=contract_id2,
            ) | models.Q(
                asset1__contract_id=contract_id2,
                asset2__contract_id=contract_id1,
            ),
        )

    def filter_for_contract(self, contract_id: str):
        return self.filter(
            models.Q(asset1__contract_id=contract_id) | models.Q(asset2__contract_id=contract_id),
        )


class MarketKey(models.Model):
    account_id = models.CharField(max_length=56, unique=True)

    asset1 = models.ForeignKey(Asset, related_name='+', on_delete=models.DO_NOTHING)
    asset2 = models.ForeignKey(Asset, related_name='+', on_delete=models.DO_NOTHING)

    created_at = models.DateTimeField(auto_now_add=True)
    locked_at = models.DateTimeField()

    is_active = models.BooleanField(default=False)

    objects = MarketKeyQuerySet.as_manager()

    def __str__(self):
        return f'MarketKey - {self.asset1.code} - {self.asset2.code}'

    def get_contract_pair(self) -> frozenset:
        """Network-agnostic pair identity based on contract ids (works for classic and soroban)."""
        return frozenset((self.asset1.contract_id, self.asset2.contract_id))

    @property
    def voting_boost(self) -> Decimal:
        return self.asset1.voting_boost + self.asset2.voting_boost
