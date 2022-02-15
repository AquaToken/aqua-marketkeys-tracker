from rest_framework import serializers

from aqua_marketkeys_tracker.marketkeys.models import MarketKey
from aqua_marketkeys_tracker.utils.stellar.asset import get_asset_string


class MarketKeySerializer(serializers.ModelSerializer):
    upvote_account_id = serializers.CharField(source='account_id')

    asset1 = serializers.SerializerMethodField()
    asset2 = serializers.SerializerMethodField()

    asset1_code = serializers.CharField(source='asset1.code')
    asset1_issuer = serializers.CharField(source='asset1.issuer')
    asset2_code = serializers.CharField(source='asset2.code')
    asset2_issuer = serializers.CharField(source='asset2.issuer')

    is_banned = serializers.BooleanField()

    voting_boost = serializers.DecimalField(max_digits=5, decimal_places=4)
    voting_boost_cap = serializers.DecimalField(max_digits=5, decimal_places=4)

    class Meta:
        model = MarketKey
        fields = ['id', 'account_id',
                  'upvote_account_id', 'downvote_account_id',
                  'asset1', 'asset1_code', 'asset1_issuer',
                  'asset2', 'asset2_code', 'asset2_issuer',
                  'is_banned',
                  'voting_boost', 'voting_boost_cap',
                  'is_auth_required',
                  'created_at', 'locked_at']

    def get_asset1(self, obj):
        return get_asset_string(obj.asset1.get_stellar_asset())

    def get_asset2(self, obj):
        return get_asset_string(obj.asset2.get_stellar_asset())
