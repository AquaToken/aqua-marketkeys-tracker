from rest_framework import serializers

from aqua_marketkeys_tracker.marketkeys.models import MarketKey


class MarketKeySerializer(serializers.ModelSerializer):
    upvote_account_id = serializers.CharField(source='account_id')

    asset1 = serializers.SerializerMethodField()
    asset2 = serializers.SerializerMethodField()

    asset1_code = serializers.CharField(source='asset1.code')
    asset1_issuer = serializers.CharField(source='asset1.issuer')
    asset2_code = serializers.CharField(source='asset2.code')
    asset2_issuer = serializers.CharField(source='asset2.issuer')

    asset1_contract = serializers.CharField(source='asset1.contract_id')
    asset2_contract = serializers.CharField(source='asset2.contract_id')
    asset1_is_sac = serializers.BooleanField(source='asset1.is_sac')
    asset2_is_sac = serializers.BooleanField(source='asset2.is_sac')

    voting_boost = serializers.DecimalField(max_digits=5, decimal_places=4)
    whitelisted_for_rewards = serializers.SerializerMethodField()
    asset1_in_asset_registry = serializers.BooleanField(source='asset1.in_asset_registry')
    asset2_in_asset_registry = serializers.BooleanField(source='asset2.in_asset_registry')

    class Meta:
        model = MarketKey
        fields = ['id', 'account_id',
                  'upvote_account_id',
                  'asset1', 'asset1_code', 'asset1_issuer',
                  'asset2', 'asset2_code', 'asset2_issuer',
                  'asset1_contract', 'asset2_contract',
                  'asset1_is_sac', 'asset2_is_sac',
                  'voting_boost',
                  'created_at', 'locked_at',
                  'whitelisted_for_rewards', 'asset1_in_asset_registry',
                  'asset2_in_asset_registry']

    def get_asset1(self, obj):
        return obj.asset1.get_asset_string()

    def get_asset2(self, obj):
        return obj.asset2.get_asset_string()

    def get_whitelisted_for_rewards(self, obj):
        return obj.asset1.in_asset_registry and obj.asset2.in_asset_registry
