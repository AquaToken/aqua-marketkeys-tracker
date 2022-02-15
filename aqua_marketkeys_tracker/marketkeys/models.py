from django.db import models
from django.db.transaction import atomic
from django.utils import timezone

from stellar_sdk import Asset as StellarAsset

from aqua_marketkeys_tracker.marketkeys.pair import MarketPair
from aqua_marketkeys_tracker.utils.stellar.asset import get_asset_string


class AssetQuerySet(models.QuerySet):
    def get_chunk(self, cursor, chunk_size):
        return self.order_by('id').filter(id__gt=cursor)[:chunk_size]


class Asset(models.Model):
    code = models.CharField(max_length=12)
    issuer = models.CharField(max_length=56)

    is_banned = models.BooleanField(default=False)

    objects = AssetQuerySet.as_manager()

    class Meta:
        unique_together = ['code', 'issuer']
        indexes = [
            models.Index(fields=['code', 'issuer']),
        ]

    def __str__(self):
        return get_asset_string(self.get_stellar_asset())

    def get_stellar_asset(self) -> StellarAsset:
        return StellarAsset(self.code, self.issuer or None)

    def set_ban(self, reason: str):
        with atomic():
            if AssetBan.objects.filter(asset=self, reason=reason, status=AssetBan.Status.BANNED).exists():
                return

            self.is_banned = True
            self.save(update_fields=['is_banned'])
            AssetBan.objects.create(
                asset=self,
                reason=reason,
                status=AssetBan.Status.BANNED,
            )

    def reset_ban(self, reason: str):
        if not AssetBan.objects.filter(asset=self, reason=reason, status=AssetBan.Status.BANNED).exists():
            return

        AssetBan.objects.filter(
            asset=self, reason=reason, status=AssetBan.Status.BANNED,
        ).update(
            status=AssetBan.Status.FIXED, fixed_at=timezone.now(),
        )


class MarketKeyQuerySet(models.QuerySet):
    def filter_active(self):
        return self.filter(is_active=True)

    def filter_for_market_pair(self, market_pair: MarketPair):
        return self.filter(
            models.Q(
                asset1__code=market_pair.asset1.code,
                asset1__issuer=market_pair.asset1.issuer or '',
                asset2__code=market_pair.asset2.code,
                asset2__issuer=market_pair.asset2.issuer or '',
            ) | models.Q(
                asset1__code=market_pair.asset2.code,
                asset1__issuer=market_pair.asset2.issuer or '',
                asset2__code=market_pair.asset1.code,
                asset2__issuer=market_pair.asset1.issuer or '',
            ),
        )

    def filter_for_asset(self, asset: StellarAsset):
        return self.filter(
            models.Q(
                asset1__code=asset.code,
                asset1__issuer=asset.issuer or '',
            ) | models.Q(
                asset2__code=asset.code,
                asset2__issuer=asset.issuer or '',
            ),
        )


class MarketKey(models.Model):
    account_id = models.CharField(max_length=56, unique=True)
    downvote_account_id = models.CharField(max_length=56, unique=True, null=True)

    asset1 = models.ForeignKey(Asset, related_name='+', on_delete=models.DO_NOTHING)
    asset2 = models.ForeignKey(Asset, related_name='+', on_delete=models.DO_NOTHING)

    created_at = models.DateTimeField(auto_now_add=True)
    locked_at = models.DateTimeField()

    is_active = models.BooleanField(default=False)
    # Deprecated
    is_auth_required = models.BooleanField(default=False)

    objects = MarketKeyQuerySet.as_manager()

    def __str__(self):
        return f'MarketKey - {self.asset1.code} - {self.asset2.code}'

    def get_market_pair(self):
        return MarketPair(
            self.asset1.get_stellar_asset(),
            self.asset2.get_stellar_asset(),
        )


class AssetBanQuerySet(models.QuerySet):
    def filter_for_unban(self):
        model = self.model
        now = timezone.now()
        return self.filter(status=model.Status.FIXED, fixed_at__lt=now - model.UNBAN_TERM)


class AssetBan(models.Model):
    UNBAN_TERM = timezone.timedelta(days=7)

    class Reason(models.TextChoices):
        AUTH_REQUIRED = 'auth_req'
        ISOLATED_MARKET = 'isolated'

    class Status(models.TextChoices):
        BANNED = 'ban'
        FIXED = 'fixed'
        UNBANNED = 'unban'

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='bans')
    reason = models.CharField(max_length=8, choices=Reason.choices)
    status = models.CharField(max_length=5, choices=Status.choices)

    banned_at = models.DateTimeField(auto_now_add=True)
    fixed_at = models.DateTimeField(null=True)
    unbanned_at = models.DateTimeField(null=True)

    objects = AssetBanQuerySet.as_manager()

    def __str__(self):
        return f'Ban for {self.asset}'

    def unban_asset(self):
        with atomic():
            if not AssetBan.objects.filter(asset=self.asset, status=self.Status.BANNED).exists():
                self.asset.is_banned = False
                self.asset.save(update_fields=['is_banned'])

            self.status = self.Status.UNBANNED
            self.unbanned_at = timezone.now()
            self.save()
