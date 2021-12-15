from rest_framework import serializers

from aqua_marketkeys_tracker.marketkeys.models import MarketKey
from aqua_marketkeys_tracker.utils.stellar.asset import get_asset_string


class MarketKeySerializer(serializers.ModelSerializer):
    upvote_account_id = serializers.CharField(source='account_id')

    asset1 = serializers.SerializerMethodField()
    asset2 = serializers.SerializerMethodField()

    class Meta:
        model = MarketKey
        fields = ['id', 'account_id',
                  'upvote_account_id', 'downvote_account_id',
                  'asset1', 'asset1_code', 'asset1_issuer',
                  'asset2', 'asset2_code', 'asset2_issuer',
                  'created_at', 'locked_at']

    def get_asset1(self, obj):
        return get_asset_string(obj.get_asset1())

    def get_asset2(self, obj):
        return get_asset_string(obj.get_asset2())
