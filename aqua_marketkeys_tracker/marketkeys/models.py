from django.db import models
from stellar_sdk import Asset

from aqua_marketkeys_tracker.marketkeys.pair import MarketPair


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
            )
            |
            models.Q(
                asset1_code=market_pair.asset2.code,
                asset1_issuer=market_pair.asset2.issuer or '',
                asset2_code=market_pair.asset1.code,
                asset2_issuer=market_pair.asset1.issuer or '',
            )
        )

    def filter_for_asset(self, asset: Asset):
        return self.filter(
            models.Q(
                asset1_code=asset.code,
                asset1_issuer=asset.issuer or '',
            )
            |
            models.Q(
                asset2_code=asset.code,
                asset2_issuer=asset.issuer or '',
            )
        )


class MarketKey(models.Model):
    account_id = models.CharField(max_length=56, unique=True)

    asset1_code = models.CharField(max_length=12)
    asset1_issuer = models.CharField(max_length=56)

    asset2_code = models.CharField(max_length=12)
    asset2_issuer = models.CharField(max_length=56)

    created_at = models.DateTimeField(auto_now_add=True)
    locked_at = models.DateTimeField()

    is_active = models.BooleanField(default=False)

    objects = MarketKeyQuerySet.as_manager()

    def __str__(self):
        return f'MarketKey - {self.asset1_code} - {self.asset2_code}'

    def get_market_pair(self):
        return MarketPair(
            self.get_asset1(),
            self.get_asset2(),
        )

    def get_asset1(self):
        return Asset(self.asset1_code, self.asset1_issuer or None)

    def get_asset2(self):
        return Asset(self.asset2_code, self.asset2_issuer or None)
