from django.db import models

from stellar_sdk import Asset as StellarAsset

from aqua_marketkeys_tracker.marketkeys.pair import MarketPair
from aqua_marketkeys_tracker.utils.stellar.asset import get_asset_string


class Asset(models.Model):
    code = models.CharField(max_length=12)
    issuer = models.CharField(max_length=56)

    is_banned = models.BooleanField(default=False)

    class Meta:
        unique_together = ['code', 'issuer']
        indexes = [
            models.Index(fields=['code', 'issuer']),
        ]

    def __str__(self):
        return get_asset_string(self.get_stellar_asset())

    def get_stellar_asset(self) -> StellarAsset:
        return StellarAsset(self.code, self.issuer)


class MarketKeyQuerySet(models.QuerySet):
    def filter_active(self):
        return self.filter(is_active=True)

    def filter_for_market_pair(self, market_pair: MarketPair):
        return self.filter(
            models.Q(
                asset1_code=market_pair.asset1.code,
                asset1_issuer=market_pair.asset1.issuer or '',
                asset2_code=market_pair.asset2.code,
                asset2_issuer=market_pair.asset2.issuer or '',
            ) | models.Q(
                asset1_code=market_pair.asset2.code,
                asset1_issuer=market_pair.asset2.issuer or '',
                asset2_code=market_pair.asset1.code,
                asset2_issuer=market_pair.asset1.issuer or '',
            ),
        )

    def filter_for_asset(self, asset: StellarAsset):
        return self.filter(
            models.Q(
                asset1_code=asset.code,
                asset1_issuer=asset.issuer or '',
            ) | models.Q(
                asset2_code=asset.code,
                asset2_issuer=asset.issuer or '',
            ),
        )


class MarketKey(models.Model):
    account_id = models.CharField(max_length=56, unique=True)
    downvote_account_id = models.CharField(max_length=56, unique=True, null=True)

    asset1 = models.ForeignKey(Asset, related_name='+', on_delete=models.DO_NOTHING, null=True)
    asset2 = models.ForeignKey(Asset, related_name='+', on_delete=models.DO_NOTHING, null=True)

    asset1_code = models.CharField(max_length=12)
    asset1_issuer = models.CharField(max_length=56)

    asset2_code = models.CharField(max_length=12)
    asset2_issuer = models.CharField(max_length=56)

    created_at = models.DateTimeField(auto_now_add=True)
    locked_at = models.DateTimeField()

    is_active = models.BooleanField(default=False)
    is_auth_required = models.BooleanField(default=False)

    objects = MarketKeyQuerySet.as_manager()

    def __str__(self):
        return f'MarketKey - {self.asset1_code} - {self.asset2_code}'

    def get_market_pair(self):
        return MarketPair(
            self.get_asset1(),
            self.get_asset2(),
        )

    def get_asset1(self):
        return StellarAsset(self.asset1_code, self.asset1_issuer or None)

    def get_asset2(self):
        return StellarAsset(self.asset2_code, self.asset2_issuer or None)
