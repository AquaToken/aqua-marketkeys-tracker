from django.contrib import admin

from aqua_marketkeys_tracker.marketkeys.models import MarketKey


@admin.register(MarketKey)
class MarketKeyAdmin(admin.ModelAdmin):
    list_display = ['account_id', 'asset1', 'asset2', 'is_active', 'locked_at']
    readonly_fields = ['account_id', 'downvote_account_id', 'locked_at']
    ordering = ['locked_at']
