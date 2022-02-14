from django.core.management import BaseCommand
from django.db import models
from stellar_sdk import Asset as StellarAsset

from aqua_marketkeys_tracker.marketkeys.models import MarketKey, Asset
from aqua_marketkeys_tracker.utils.stellar.asset import get_asset_string


# Deprecated
class Command(BaseCommand):
    def create_asset(self, asset: StellarAsset) -> Asset:
        asset_string = get_asset_string(asset)

        if asset_string in self.assets_cache:
            return self.assets_cache[asset_string]

        code = asset.code
        issuer = asset.issuer or ''
        self.assets_cache[asset_string] = Asset.objects.get_or_create(code=code, issuer=issuer)[0]
        return self.assets_cache[asset_string]

    def handle(self, *args, **options):
        self.assets_cache = {}
        queryset = MarketKey.objects.filter(
            models.Q(asset1__isnull=True)
            | models.Q(asset2__isnull=True)
        )
        for market_key in queryset:
            if not market_key.asset1:
                market_key.asset1 = self.create_asset(market_key.get_asset1())
            if not market_key.asset2:
                market_key.asset2 = self.create_asset(market_key.get_asset2())
            market_key.save(update_fields=['asset1', 'asset2'])
