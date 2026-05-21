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

    # todo: drop the following five fields after frontend stops reading them
    is_banned = serializers.SerializerMethodField()
    auth_required = serializers.SerializerMethodField()
    auth_revocable = serializers.SerializerMethodField()
    auth_clawback_enabled = serializers.SerializerMethodField()
    no_liquidity = serializers.SerializerMethodField()

    voting_boost = serializers.DecimalField(max_digits=5, decimal_places=4)
    downvote_immunity = serializers.BooleanField()
    whitelisted_for_rewards = serializers.SerializerMethodField()
    asset1_in_asset_registry = serializers.BooleanField(source='asset1.in_asset_registry')
    asset2_in_asset_registry = serializers.BooleanField(source='asset2.in_asset_registry')

    class Meta:
        model = MarketKey
        fields = ['id', 'account_id',
                  'upvote_account_id', 'downvote_account_id',
                  'asset1', 'asset1_code', 'asset1_issuer',
                  'asset2', 'asset2_code', 'asset2_issuer',
                  'is_banned', 'auth_required', 'auth_revocable',
                  'auth_clawback_enabled', 'no_liquidity',
                  'voting_boost', 'downvote_immunity',
                  'created_at', 'locked_at',
                  'whitelisted_for_rewards', 'asset1_in_asset_registry',
                  'asset2_in_asset_registry']

    def get_asset1(self, obj):
        return get_asset_string(obj.asset1.get_stellar_asset())

    def get_asset2(self, obj):
        return get_asset_string(obj.asset2.get_stellar_asset())

    def get_is_banned(self, _obj):
        return False

    def get_auth_required(self, _obj):
        return False

    def get_auth_revocable(self, _obj):
        return False

    def get_auth_clawback_enabled(self, _obj):
        return False

    def get_no_liquidity(self, _obj):
        return False

    def get_whitelisted_for_rewards(self, obj):
        return obj.asset1.in_asset_registry and obj.asset2.in_asset_registry
